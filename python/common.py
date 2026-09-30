"""Shared token, tree, and error types.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Token:
    kind: str
    text: str
    position: int  # Character index in the original input, including whitespace.
    value: int = 0  # Used only for number tokens.


class CompileError(Exception):
    def __init__(self, position, message):
        super().__init__(message)
        self.position = position


@dataclass
class Type:
    kind: str
    base: Optional["Type"] = None
    name: Optional[Token] = field(default=None, compare=False)
    return_ty: Optional["Type"] = None
    params: list["Type"] = field(default_factory=list)
    size: int = 0
    array_len: int = 0


@dataclass
class Obj:
    name: str
    offset: int = 0
    ty: Optional[Type] = field(default=None, compare=False)


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
    args: list["Node"] = field(default_factory=list)


@dataclass
class Function:
    body: Node
    locals: list[Obj]
    stack_size: int = 0
    name: str = "main"
    params: list[Obj] = field(default_factory=list)
