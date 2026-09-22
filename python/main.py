"""Lesson 1: compile one decimal integer into x86-64 Linux assembly.

Based on chibicc commit 0522e2d77e3ab82d3b80a5be8dbbdc8d4180561c.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import re
import sys


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    source = sys.argv[1].strip()
    if re.fullmatch(r"[+-]?[0-9]+", source) is None:
        print("expected a decimal integer", file=sys.stderr)
        return 1

    try:
        value = int(source, 10)
    except ValueError:
        print("integer is too large to convert", file=sys.stderr)
        return 1
    if not -(2**31) <= value < 2**31:
        print("integer must fit in a signed 32-bit C int", file=sys.stderr)
        return 1

    print("  .globl main")
    print("main:")
    print(f"  mov ${value}, %rax")
    print("  ret")
    return 0


if __name__ == "__main__":
    sys.exit(main())
