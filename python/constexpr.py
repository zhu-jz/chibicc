"""Evaluate compiler syntax trees for enum values, bounds, and case labels.

Based on chibicc commit 79f5de21eb706ea5486fd682a83ffbde7e4d16a9.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError
from type import add_type, is_integer


def evaluate_initializer(node):
    """Return an integer addend and an optional global symbol name."""
    add_type(node)
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
        if is_integer(node.ty) and node.ty.size in (1, 2, 4):
            value &= (1 << (node.ty.size * 8)) - 1
        return value, label
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


def evaluate_constant(node):
    add_type(node)
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
        if is_integer(node.ty) and node.ty.size in (1, 2, 4):
            return value & ((1 << (node.ty.size * 8)) - 1)
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
        return left << right if kind == "<<" else left >> right
    if kind == "==":
        return int(left == right)
    if kind == "!=":
        return int(left != right)
    if kind == "<":
        return int(left < right)
    return int(left <= right)
