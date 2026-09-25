"""Shared token, tree, and error types.

Based on chibicc commit 482c26b536f8e5c998af6210470cd3d97a47ee9a.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass
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
class Obj:
    name: str
    offset: int = 0


@dataclass
class Node:
    kind: str
    lhs: Optional["Node"] = None
    rhs: Optional["Node"] = None
    value: int = 0
    var: Optional[Obj] = None  # Shared local-variable object for VAR nodes.


@dataclass
class Function:
    body: list[Node]
    locals: list[Obj]
    stack_size: int = 0
