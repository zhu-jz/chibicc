"""Shared token, tree, and error types.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass, field
from typing import Optional


def align_to(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def to_int32(value):
    value &= 0xffffffff
    return value - 0x100000000 if value >= 0x80000000 else value


@dataclass
class Token:
    kind: str
    text: str
    position: int  # Character index in the original input, including whitespace.
    value: int = 0  # Used only for number tokens.
    ty: Optional["Type"] = field(default=None, compare=False)
    str: bytes = b""  # String bytes, including the terminating zero.
    line_no: int = field(default=0, compare=False)


class CompileError(Exception):
    def __init__(self, position, message):
        super().__init__(message)
        if isinstance(position, Token):
            self.position = position.position
            self.line_no = position.line_no or None
        else:
            self.position = position
            self.line_no = None


@dataclass
class Type:
    kind: str
    base: Optional["Type"] = None
    name: Optional[Token] = field(default=None, compare=False)
    return_ty: Optional["Type"] = None
    params: list["Type"] = field(default_factory=list)
    size: int = 0
    array_len: int = 0
    members: list["Member"] = field(default_factory=list)
    align: int = 0


@dataclass
class Member:
    ty: Type
    name: Token
    offset: int = 0
    tok: Optional[Token] = field(default=None, compare=False)


@dataclass
class Obj:
    name: str
    offset: int = 0
    ty: Optional[Type] = field(default=None, compare=False)
    is_local: bool = False
    is_function: bool = False
    is_definition: bool = False
    is_static: bool = False
    params: list["Obj"] = field(default_factory=list)
    body: Optional["Node"] = None
    locals: list["Obj"] = field(default_factory=list)
    stack_size: int = 0
    init_data: Optional[bytes] = None


@dataclass
class VarScope:
    name: str
    var: Optional[Obj] = None
    type_def: Optional[Type] = None
    enum_ty: Optional[Type] = None
    enum_val: int = 0


@dataclass
class VarAttr:
    is_typedef: bool = False
    is_static: bool = False


@dataclass
class Scope:
    vars: list[VarScope] = field(default_factory=list)
    tags: dict[str, Type] = field(default_factory=dict)


@dataclass
class Node:
    kind: str
    lhs: Optional["Node"] = None
    rhs: Optional["Node"] = None
    value: int = 0
    var: Optional[Obj] = None  # Shared local-variable object for VAR nodes.
    body: list["Node"] = field(default_factory=list)  # Statements in a BLOCK.
    cond: Optional["Node"] = None
    then: Optional["Node"] = None
    els: Optional["Node"] = None
    init: Optional["Node"] = None
    inc: Optional["Node"] = None
    tok: Optional[Token] = field(default=None, compare=False)  # Source metadata.
    ty: Optional[Type] = field(default=None, compare=False)  # Inferred type.
    funcname: str = ""
    func_ty: Optional[Type] = field(default=None, compare=False)
    args: list["Node"] = field(default_factory=list)
    member: Optional[Member] = None
    label: str = ""
    unique_label: Optional[str] = field(default=None, compare=False)
    brk_label: Optional[str] = field(default=None, compare=False)
    cont_label: Optional[str] = field(default=None, compare=False)
    cases: list["Node"] = field(default_factory=list, compare=False)
    default_case: Optional["Node"] = field(default=None, compare=False)


@dataclass
class Initializer:
    ty: Type
    tok: Optional[Token] = None
    expr: Optional[Node] = None
    children: list["Initializer"] = field(default_factory=list)
    is_flexible: bool = False


@dataclass
class InitDesg:
    parent: Optional["InitDesg"] = None
    idx: int = 0
    var: Optional[Obj] = None
