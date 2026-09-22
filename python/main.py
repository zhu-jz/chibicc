"""Lesson 2: compile addition and subtraction into x86-64 Linux assembly.

Based on chibicc commit bf7081fba7d8c6b1cd8a12eb329697a5481c604e.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import re
import sys


def read_number(source, position):
    # Like strtol, consume whitespace, an optional sign, and decimal digits.
    match = re.match(r"\s*[+-]?[0-9]+", source[position:])
    if match is None:
        raise ValueError("expected a decimal integer")

    value = int(match.group(), 10)
    if not -(2**31) <= value < 2**31:
        raise ValueError("integer must fit in a signed 32-bit immediate")
    return value, position + match.end()


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    source = sys.argv[1].strip()
    try:
        value, position = read_number(source, 0)
        assembly = ["  .globl main", "main:", f"  mov ${value}, %rax"]

        while position < len(source):
            operator = source[position]
            if operator == "+":
                instruction = "add"
            elif operator == "-":
                instruction = "sub"
            else:
                raise ValueError(f"unexpected character: {operator!r}")

            position += 1
            value, position = read_number(source, position)
            assembly.append(f"  {instruction} ${value}, %rax")

        assembly.append("  ret")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    print("\n".join(assembly))
    return 0


if __name__ == "__main__":
    sys.exit(main())
