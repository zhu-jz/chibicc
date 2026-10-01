"""Shared token, tree, and error types.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass, field
from typing import Optional
from unicode import display_width


def align_to(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def to_int32(value):
    value &= 0xffffffff
    return value - 0x100000000 if value >= 0x80000000 else value


@dataclass
class File:
    name: str
    file_no: int
    contents: str
    display_name: Optional[str] = None
    line_delta: int = 0

    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.name


def format_diagnostic(file: File, position: int, message: str,
                      line_no: Optional[int] = None) -> str:
    source = file.contents
    line_start = source.rfind("\n", 0, position) + 1
    line_end = source.find("\n", position)
    if line_end == -1:
        line_end = len(source)
    line_no = line_no or source.count("\n", 0, line_start) + 1
    prefix = f"{file.name}:{line_no}: "
    caret = " " * (len(prefix) + display_width(source[line_start:position])) + "^ " + message
    return prefix + source[line_start:line_end] + "\n" + caret


@dataclass
class Token:
    kind: str
    text: str
    position: int  # Character index in the original input, including whitespace.
    value: int = 0  # Used only for number tokens.
    ty: Optional["Type"] = field(default=None, compare=False)
    str: bytes = b""  # String bytes, including the terminating zero.
    line_no: int = field(default=0, compare=False)
    fvalue: float = 0.0

    at_bol: bool = field(default=False, compare=False)
    has_space: bool = field(default=False, compare=False)
    file: Optional[File] = field(default=None, compare=False)
    hideset: frozenset[str] = field(default_factory=frozenset, compare=False)
    origin: Optional["Token"] = field(default=None, compare=False, repr=False)
    filename: Optional["str"] = field(default=None, compare=False)
    line_delta: int = field(default=0, compare=False)


class CompileError(Exception):
    def __init__(self, position, message: str):
        super().__init__(message)
        if isinstance(position, Token):
            self.position = position.position
            self.line_no = position.line_no or None
            self.file = position.file
        else:
            self.position = position
            self.line_no = None
            self.file = None


@dataclass
class Type:
    kind: str
    base: Optional["Type"] = None
    name: Optional[Token] = field(default=None, compare=False)
    name_pos: Optional[Token] = field(default=None, compare=False)
    return_ty: Optional["Type"] = None
    params: list["Type"] = field(default_factory=list)
    size: int = 0
    array_len: int = 0
    vla_len: Optional["Node"] = field(default=None, compare=False)
    vla_size: Optional["Obj"] = field(default=None, compare=False, repr=False)
    members: list["Member"] = field(default_factory=list)
    align: int = 0
    is_flexible: bool = False
    is_variadic: bool = False
    is_unsigned: bool = False
    origin: Optional["Type"] = field(default=None, compare=False, repr=False)


@dataclass
class Member:
    ty: Type
    name: Optional[Token]
    offset: int = 0
    tok: Optional[Token] = field(default=None, compare=False)
    idx: int = 0
    align: int = field(default=0, compare=False)
    is_bitfield: bool = False
    bit_offset: int = 0
    bit_width: int = 0


@dataclass
class Relocation:
    offset: int
    label: "str | Node"
    addend: int


@dataclass
class Obj:
    name: str
    offset: int = 0
    ty: Optional[Type] = field(default=None, compare=False)
    is_local: bool = False
    is_function: bool = False
    is_definition: bool = False
    is_static: bool = False
    is_tentative: bool = False
    is_tls: bool = False
    params: list["Obj"] = field(default_factory=list)
    is_inline: bool = False
    is_live: bool = field(default=False, compare=False)
    is_root: bool = field(default=False, compare=False)
    refs: list[str] = field(default_factory=list, compare=False)
    body: Optional["Node"] = None
    locals: list["Obj"] = field(default_factory=list)
    stack_size: int = 0
    init_data: Optional[bytes] = None
    relocations: list[Relocation] = field(default_factory=list)
    align: int = field(default=0, compare=False)
    va_area: Optional["Obj"] = field(default=None, compare=False)
    alloca_bottom: Optional["Obj"] = field(default=None, compare=False, repr=False)
    tok: Optional[Token] = field(default=None, compare=False)


@dataclass
class VarScope:
    var: Optional[Obj] = None
    type_def: Optional[Type] = None
    enum_ty: Optional[Type] = None
    enum_val: int = 0


@dataclass
class VarAttr:
    is_typedef: bool = False
    is_static: bool = False
    is_extern: bool = False
    is_inline: bool = False
    is_tls: bool = False
    align: int = 0


@dataclass
class Scope:
    vars: dict[str, VarScope] = field(default_factory=dict)
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
    func_ty: Optional[Type] = field(default=None, compare=False)
    args: list["Node"] = field(default_factory=list)
    pass_by_stack: bool = field(default=False, compare=False)
    ret_buffer: Optional["Obj"] = field(default=None, compare=False)
    member: Optional[Member] = None
    label: str = ""
    unique_label: Optional[str] = field(default=None, compare=False)
    brk_label: Optional[str] = field(default=None, compare=False)
    cont_label: Optional[str] = field(default=None, compare=False)
    cases: list["Node"] = field(default_factory=list, compare=False)
    begin: int = 0
    end: int = 0
    default_case: Optional["Node"] = field(default=None, compare=False)
    fvalue: float = 0.0
    asm_str: str = ""


@dataclass
class Initializer:
    ty: Type
    tok: Optional[Token] = None
    expr: Optional[Node] = None
    children: list["Initializer"] = field(default_factory=list)
    member: Optional[Member] = None
    is_flexible: bool = False


@dataclass
class InitDesg:
    parent: Optional["InitDesg"] = None
    idx: int = 0
    member: Optional[Member] = None
    var: Optional[Obj] = None
