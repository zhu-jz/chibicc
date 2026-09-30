"""Annotate expression nodes with integer or pointer types.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import replace

from common import CompileError, Type


ty_char = Type("CHAR", size=1)
ty_int = Type("INT", size=8)


def is_integer(ty):
    return ty.kind in ("CHAR", "INT")


def copy_type(ty):
    return replace(ty)


def pointer_to(base):
    return Type("PTR", base, size=8)


def func_type(return_ty):
    return Type("FUNC", return_ty=return_ty)


def array_of(base, length):
    return Type("ARRAY", base, size=base.size * length, array_len=length)


def add_type(node):
    if node is None or node.ty is not None:
        return

    for child in (node.lhs, node.rhs, node.cond, node.then, node.els,
                  node.init, node.inc):
        add_type(child)
    for statement in node.body:
        add_type(statement)
    for arg in node.args:
        add_type(arg)

    if node.kind in ("+", "-", "*", "/", "NEG"):
        node.ty = node.lhs.ty
    elif node.kind == "ASSIGN":
        if node.lhs.ty.kind == "ARRAY":
            raise CompileError(node.lhs.tok, "not an lvalue")
        node.ty = node.lhs.ty
    elif node.kind in ("==", "!=", "<", "<=", "NUM", "FUNCALL"):
        node.ty = ty_int
    elif node.kind == "VAR":
        node.ty = node.var.ty
    elif node.kind == "ADDR":
        if node.lhs.ty.kind == "ARRAY":
            node.ty = pointer_to(node.lhs.ty.base)
        else:
            node.ty = pointer_to(node.lhs.ty)
    elif node.kind == "DEREF":
        if node.lhs.ty.base is None:
            raise CompileError(node.tok, "invalid pointer dereference")
        node.ty = node.lhs.ty.base
    elif node.kind == "STMT_EXPR":
        if node.body and node.body[-1].kind == "EXPR_STMT":
            node.ty = node.body[-1].lhs.ty
        else:
            raise CompileError(node.tok,
                               "statement expression returning void is not supported")
