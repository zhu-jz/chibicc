"""Annotate expression nodes with integer or pointer types.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import replace

from common import CompileError, Node, Type


ty_void = Type("VOID", size=1, align=1)
ty_bool = Type("BOOL", size=1, align=1)
ty_char = Type("CHAR", size=1, align=1)
ty_short = Type("SHORT", size=2, align=2)
ty_int = Type("INT", size=4, align=4)
ty_long = Type("LONG", size=8, align=8)
ty_uchar = Type("CHAR", size=1, align=1, is_unsigned=True)
ty_ushort = Type("SHORT", size=2, align=2, is_unsigned=True)
ty_uint = Type("INT", size=4, align=4, is_unsigned=True)
ty_ulong = Type("LONG", size=8, align=8, is_unsigned=True)


def is_integer(ty):
    return ty.kind in ("BOOL", "CHAR", "SHORT", "INT", "LONG", "ENUM")


def copy_type(ty):
    return replace(ty)


def pointer_to(base):
    return Type("PTR", base, size=8, align=8, is_unsigned=True)


def func_type(return_ty):
    return Type("FUNC", return_ty=return_ty)


def array_of(base, length):
    return Type("ARRAY", base, size=base.size * length, array_len=length, align=base.align)


def enum_type():
    return Type("ENUM", size=4, align=4)


def struct_type():
    return Type("STRUCT", size=0, align=1)


def new_cast(expression, ty):
    add_type(expression)
    return Node("CAST", lhs=expression, ty=copy_type(ty), tok=expression.tok)


def get_common_type(left, right):
    if left.base is not None:
        return pointer_to(left.base)
    if left.size < 4:
        left = ty_int
    if right.size < 4:
        right = ty_int
    if left.size != right.size:
        return right if left.size < right.size else left
    return right if right.is_unsigned else left


def usual_arith_conv(left, right):
    ty = get_common_type(left.ty, right.ty)
    return new_cast(left, ty), new_cast(right, ty)


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

    if node.kind == "NUM":
        node.ty = ty_int
    elif node.kind in ("+", "-", "*", "/", "%", "&", "|", "^"):
        node.lhs, node.rhs = usual_arith_conv(node.lhs, node.rhs)
        node.ty = node.lhs.ty
    elif node.kind == "NEG":
        node.ty = get_common_type(ty_int, node.lhs.ty)
        node.lhs = new_cast(node.lhs, node.ty)
    elif node.kind == "ASSIGN":
        if node.lhs.ty.kind == "ARRAY":
            raise CompileError(node.lhs.tok, "not an lvalue")
        if node.lhs.ty.kind != "STRUCT":
            node.rhs = new_cast(node.rhs, node.lhs.ty)
        node.ty = node.lhs.ty
    elif node.kind in ("==", "!=", "<", "<="):
        node.lhs, node.rhs = usual_arith_conv(node.lhs, node.rhs)
        node.ty = ty_int
    elif node.kind == "FUNCALL":
        node.ty = ty_long
    elif node.kind in ("NOT", "LOGAND", "LOGOR"):
        node.ty = ty_int
    elif node.kind in ("BITNOT", "<<", ">>"):
        node.ty = node.lhs.ty
    elif node.kind == "VAR":
        node.ty = node.var.ty
    elif node.kind == "COND":
        if node.then.ty.kind == "VOID" or node.els.ty.kind == "VOID":
            node.ty = ty_void
        else:
            node.then, node.els = usual_arith_conv(node.then, node.els)
            node.ty = node.then.ty
    elif node.kind == "COMMA":
        node.ty = node.rhs.ty
    elif node.kind == "MEMBER":
        node.ty = node.member.ty
    elif node.kind == "ADDR":
        if node.lhs.ty.kind == "ARRAY":
            node.ty = pointer_to(node.lhs.ty.base)
        else:
            node.ty = pointer_to(node.lhs.ty)
    elif node.kind == "DEREF":
        if node.lhs.ty.base is None:
            raise CompileError(node.tok, "invalid pointer dereference")
        if node.lhs.ty.base.kind == "VOID":
            raise CompileError(node.tok, "dereferencing a void pointer")
        node.ty = node.lhs.ty.base
    elif node.kind == "STMT_EXPR":
        if node.body and node.body[-1].kind == "EXPR_STMT":
            node.ty = node.body[-1].lhs.ty
        else:
            raise CompileError(node.tok,
                               "statement expression returning void is not supported")
