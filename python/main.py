"""Lesson 3: tokenize numbers and operators before generating assembly.

Based on chibicc commit a1ab0ff26f23c82f15180051204eeb6279747c9a.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import dataclass
import sys


@dataclass
class Token:
    kind: str
    text: str
    value: int = 0  # Used only for number tokens.


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
            value = int(text, 10)
            if value > 2**31 - 1:
                raise ValueError("integer must fit in a signed 32-bit immediate")
            tokens.append(Token("NUM", text, value))
            continue

        if character in "+-":
            tokens.append(Token("PUNCT", character))
            position += 1
            continue

        raise ValueError("invalid token")

    tokens.append(Token("EOF", ""))
    return tokens


def get_number(token):
    if token.kind != "NUM":
        raise ValueError("expected a number")
    return token.value


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    try:
        tokens = tokenize(sys.argv[1])
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
                raise ValueError("expected '-'")

            value = get_number(tokens[position + 1])
            assembly.append(f"  {instruction} ${value}, %rax")
            position += 2

        assembly.append("  ret")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    print("\n".join(assembly))
    return 0


if __name__ == "__main__":
    sys.exit(main())
