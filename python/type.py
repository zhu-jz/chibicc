"""Annotate expression nodes with integer or pointer types.

Based on chibicc commit a6bc4ab101c20b6398fd6bbfe124665bb7db5d25.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import Type


ty_int = Type("INT")


def is_integer(ty):
    return ty.kind == "INT"


def pointer_to(base):
    return Type("PTR", base)


def add_type(node):
    if node is None or node.ty is not None:
        return

    for child in (node.lhs, node.rhs, node.cond, node.then, node.els,
                  node.init, node.inc):
        add_type(child)
    for statement in node.body:
        add_type(statement)

    if node.kind in ("+", "-", "*", "/", "NEG", "ASSIGN"):
        node.ty = node.lhs.ty
    elif node.kind in ("==", "!=", "<", "<=", "VAR", "NUM"):
        node.ty = ty_int
    elif node.kind == "ADDR":
        node.ty = pointer_to(node.lhs.ty)
    elif node.kind == "DEREF":
        if node.lhs.ty.kind == "PTR":
            node.ty = node.lhs.ty.base
        else:
            node.ty = ty_int
