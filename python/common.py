"""Shared token, tree, and error types.

Based on chibicc commit 1f9f3adf324af1432a380b41c7690834e649e346.
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
class Node:
    kind: str
    lhs: Optional["Node"] = None
    rhs: Optional["Node"] = None
    value: int = 0
    name: str = ""  # Used only for variable nodes.
