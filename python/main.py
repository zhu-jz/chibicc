"""Lesson 5: parse expression trees and compile *, /, and parentheses.

Based on chibicc commit 84cfcaf98f3d19c8f0f316e22a61725ad201f0f6.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass
import string
import sys
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


def tokenize(source):
    tokens = []
    position = 0

    while position < len(source):
        character = source[position]

        if character.isspace():
            position += 1
            continue

        if "0" <= character <= "9":
            start = position
            while position < len(source) and "0" <= source[position] <= "9":
                position += 1
            text = source[start:position]
            try:
                value = int(text, 10)
            except ValueError:
                raise CompileError(start, "integer is too large to convert") from None
            if value > 2**31 - 1:
                raise CompileError(start, "integer must fit in a signed 32-bit immediate")
            tokens.append(Token("NUM", text, start, value))
            continue

        if character in string.punctuation:
            tokens.append(Token("PUNCT", character, position))
            position += 1
            continue

        raise CompileError(position, "invalid token")

    tokens.append(Token("EOF", "", position))
    return tokens


@dataclass
class Node:
    kind: str
    lhs: Optional["Node"] = None
    rhs: Optional["Node"] = None
    value: int = 0


# Each parser function returns (node, next unconsumed token index).
# expr = mul (("+" | "-") mul)*
def expr(tokens, position):
    node, position = mul(tokens, position)
    while tokens[position].text in ("+", "-"):
        operator = tokens[position].text
        rhs, position = mul(tokens, position + 1)
        node = Node(operator, node, rhs)
    return node, position


# mul = primary (("*" | "/") primary)*
def mul(tokens, position):
    node, position = primary(tokens, position)
    while tokens[position].text in ("*", "/"):
        operator = tokens[position].text
        rhs, position = primary(tokens, position + 1)
        node = Node(operator, node, rhs)
    return node, position


# primary = "(" expr ")" | number
def primary(tokens, position):
    token = tokens[position]
    if token.text == "(":
        node, position = expr(tokens, position + 1)
        if tokens[position].text != ")":
            raise CompileError(tokens[position].position, "expected ')'")
        return node, position + 1

    if token.kind == "NUM":
        return Node("NUM", value=token.value), position + 1

    raise CompileError(token.position, "expected an expression")


class CodeGenerator:
    def __init__(self):
        self.assembly = ["  .globl main", "main:"]
        self.depth = 0

    def push(self):
        self.assembly.append("  push %rax")
        self.depth += 1

    def pop(self, register):
        self.assembly.append(f"  pop {register}")
        self.depth -= 1

    def gen_expr(self, node):
        if node.kind == "NUM":
            self.assembly.append(f"  mov ${node.value}, %rax")
            return

        # Save the right result, compute the left, then restore the right.
        self.gen_expr(node.rhs)
        self.push()
        self.gen_expr(node.lhs)
        self.pop("%rdi")

        if node.kind == "+":
            self.assembly.append("  add %rdi, %rax")
        elif node.kind == "-":
            self.assembly.append("  sub %rdi, %rax")
        elif node.kind == "*":
            self.assembly.append("  imul %rdi, %rax")
        elif node.kind == "/":
            self.assembly.append("  cqo")
            self.assembly.append("  idiv %rdi")
        else:
            raise AssertionError("invalid expression")

    def generate(self, node):
        self.gen_expr(node)
        self.assembly.append("  ret")
        assert self.depth == 0
        return "\n".join(self.assembly)


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    source = sys.argv[1]
    try:
        tokens = tokenize(source)
        node, position = expr(tokens, 0)
        if tokens[position].kind != "EOF":
            raise CompileError(tokens[position].position, "extra token")
        assembly = CodeGenerator().generate(node)
    except CompileError as error:
        print(source, file=sys.stderr)
        print(" " * error.position + "^ " + str(error), file=sys.stderr)
        return 1

    print(assembly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
