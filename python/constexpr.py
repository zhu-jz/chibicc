"""Evaluate compiler syntax trees for enum values, bounds, and case labels.

Based on chibicc commit 79f5de21eb706ea5486fd682a83ffbde7e4d16a9.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import math

from common import CompileError
from type import add_type, is_integer, is_flonum


def cast_constant(value, ty):
    if is_integer(ty) and ty.size in (1, 2, 4):
        bits = ty.size * 8
        value &= (1 << bits) - 1
        if not ty.is_unsigned and value >= 1 << (bits - 1):
            value -= 1 << bits
    return value


def signed64(value):
    return value - (1 << 64) if value >= 1 << 63 else value


def evaluate_initializer(node):
    """Return an integer addend and an optional global symbol name."""
    add_type(node)
    if is_flonum(node.ty):
        return evaluate_constant(node), None
    if node.kind in ("+", "-"):
        value, label = evaluate_initializer(node.lhs)
        right = evaluate_constant(node.rhs)
        return (value + right if node.kind == "+" else value - right), label
    if node.kind == "COND":
        branch = node.then if evaluate_constant(node.cond) else node.els
        return evaluate_initializer(branch)
    if node.kind == "COMMA":
        return evaluate_initializer(node.rhs)
    if node.kind == "CAST":
        value, label = evaluate_initializer(node.lhs)
        return cast_constant(value, node.ty), label
    if node.kind == "ADDR":
        return evaluate_address(node.lhs)
    if node.kind == "MEMBER":
        if node.ty.kind != "ARRAY":
            raise CompileError(node.tok, "invalid initializer")
        value, label = evaluate_address(node.lhs)
        return value + node.member.offset, label
    if node.kind == "VAR":
        if node.var.ty.kind not in ("ARRAY", "FUNC"):
            raise CompileError(node.tok, "invalid initializer")
        return 0, node.var.name
    return evaluate_constant(node), None


def evaluate_address(node):
    if node.kind == "VAR":
        if node.var.is_local:
            raise CompileError(node.tok, "not a compile-time constant")
        return 0, node.var.name
    if node.kind == "DEREF":
        return evaluate_initializer(node.lhs)
    if node.kind == "MEMBER":
        value, label = evaluate_address(node.lhs)
        return value + node.member.offset, label
    raise CompileError(node.tok, "invalid initializer")


def is_const_expr(node):
    add_type(node)
    if node.kind in ("+", "-", "*", "/", "&", "|", "^", "<<", ">>",
                     "==", "!=", "<", "<=", "LOGAND", "LOGOR"):
        return is_const_expr(node.lhs) and is_const_expr(node.rhs)
    if node.kind == "COND":
        if not is_const_expr(node.cond):
            return False
        return is_const_expr(node.then if evaluate_constant(node.cond) else node.els)
    if node.kind == "COMMA":
        return is_const_expr(node.rhs)
    if node.kind in ("NEG", "NOT", "BITNOT", "CAST"):
        return is_const_expr(node.lhs)
    return node.kind == "NUM"


def evaluate_constant(node):
    add_type(node)
    if is_flonum(node.ty):
        try:
            return int(evaluate_float(node))
        except (ValueError, OverflowError):
            raise CompileError(node.tok, "non-finite floating constant converted to integer") from None
    kind = node.kind
    if kind == "NUM":
        return node.value
    if kind == "NEG":
        return -evaluate_constant(node.lhs)
    if kind == "NOT":
        return int(evaluate_constant(node.lhs) == 0)
    if kind == "BITNOT":
        return ~evaluate_constant(node.lhs)
    if kind == "COND":
        branch = node.then if evaluate_constant(node.cond) else node.els
        return evaluate_constant(branch)
    if kind == "COMMA":
        return evaluate_constant(node.rhs)
    if kind == "LOGAND":
        return int(evaluate_constant(node.lhs) != 0 and evaluate_constant(node.rhs) != 0)
    if kind == "LOGOR":
        return int(evaluate_constant(node.lhs) != 0 or evaluate_constant(node.rhs) != 0)
    if kind == "CAST":
        value = evaluate_constant(node.lhs)
        return cast_constant(value, node.ty)
    if kind == "ADDR":
        value, label = evaluate_address(node.lhs)
        if label is not None:
            raise CompileError(node.tok, "not a compile-time constant")
        return value
    if kind not in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>", "==", "!=", "<", "<="):
        raise CompileError(node.tok, "not a compile-time constant")
    left = evaluate_constant(node.lhs)
    right = evaluate_constant(node.rhs)
    if kind == "+":
        return left + right
    if kind == "-":
        return left - right
    if kind == "*":
        return left * right
    if kind in ("/", "%"):
        if right == 0:
            raise CompileError(node.tok, "division by zero in constant expression")
        if node.ty.is_unsigned:
            left &= (1 << 64) - 1
            right &= (1 << 64) - 1
            return signed64(left // right if kind == "/" else left % right)
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        return quotient if kind == "/" else left - quotient * right
    if kind == "&":
        return left & right
    if kind == "|":
        return left | right
    if kind == "^":
        return left ^ right
    if kind in ("<<", ">>"):
        if not 0 <= right < 64:
            raise CompileError(node.tok, "invalid shift count in constant expression")
        if kind == ">>" and node.ty.is_unsigned and node.ty.size == 8:
            return signed64((left & ((1 << 64) - 1)) >> right)
        return left << right if kind == "<<" else left >> right
    if kind == "==":
        return int(left == right)
    if kind == "!=":
        return int(left != right)
    if kind == "<":
        if node.lhs.ty.is_unsigned:
            return int((left & ((1 << 64) - 1)) < (right & ((1 << 64) - 1)))
        return int(left < right)
    if node.lhs.ty.is_unsigned:
        return int((left & ((1 << 64) - 1)) <= (right & ((1 << 64) - 1)))
    return int(left <= right)


def evaluate_float(node):
    """Evaluate the historical floating initializer rules in double precision."""
    add_type(node)
    if is_integer(node.ty):
        value = evaluate_constant(node)
        if node.ty.is_unsigned:
            value &= (1 << 64) - 1
        return float(value)
    if node.kind == "NUM":
        return node.fvalue
    if node.kind == "NEG":
        return -evaluate_float(node.lhs)
    if node.kind == "COND":
        return evaluate_float(node.then if evaluate_float(node.cond) else node.els)
    if node.kind == "COMMA":
        return evaluate_float(node.rhs)
    if node.kind == "CAST":
        if is_flonum(node.lhs.ty):
            return evaluate_float(node.lhs)
        return float(evaluate_constant(node.lhs))
    if node.kind not in ("+", "-", "*", "/"):
        raise CompileError(node.tok, "not a compile-time constant")
    left = evaluate_float(node.lhs)
    right = evaluate_float(node.rhs)
    if node.kind == "+":
        return left + right
    if node.kind == "-":
        return left - right
    if node.kind == "*":
        return left * right
    if right == 0.0:
        if left == 0.0 or math.isnan(left):
            return math.nan
        return math.copysign(math.inf, math.copysign(1.0, left) * math.copysign(1.0, right))
    return left / right
