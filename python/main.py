"""Lesson 4: report errors with their source locations.

Based on chibicc commit cc5a6d978144bda90220bd10866c4fd908d07546.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass
import sys


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

        if character in "+-":
            tokens.append(Token("PUNCT", character, position))
            position += 1
            continue

        raise CompileError(position, "invalid token")

    tokens.append(Token("EOF", "", position))
    return tokens


def get_number(token):
    if token.kind != "NUM":
        raise CompileError(token.position, "expected a number")
    return token.value


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    source = sys.argv[1]
    try:
        tokens = tokenize(source)
        value = get_number(tokens[0])
        assembly = ["  .globl main", "main:", f"  mov ${value}, %rax"]
        position = 1

        while tokens[position].kind != "EOF":
            operator = tokens[position].text
            if operator == "+":
                instruction = "add"
            elif operator == "-":
                instruction = "sub"
            else:
                raise CompileError(tokens[position].position, "expected '-'")

            value = get_number(tokens[position + 1])
            assembly.append(f"  {instruction} ${value}, %rax")
            position += 2

        assembly.append("  ret")
    except CompileError as error:
        print(source, file=sys.stderr)
        print(" " * error.position + "^ " + str(error), file=sys.stderr)
        return 1

    print("\n".join(assembly))
    return 0


if __name__ == "__main__":
    sys.exit(main())
