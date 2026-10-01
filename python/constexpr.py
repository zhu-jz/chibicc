"""Evaluate compiler syntax trees for enum values, bounds, and case labels.

Based on chibicc commit 79f5de21eb706ea5486fd682a83ffbde7e4d16a9.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError
from type import add_type, is_integer


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
