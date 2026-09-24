"""Lesson 9: compile expression statements separated by semicolons.

Based on chibicc commit 76cae0ad05b6ba3e3e927b2b749ccddda23f0c51.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import sys

from codegen import codegen
from common import CompileError
from parse import parse
from tokenizer import tokenize


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    source = sys.argv[1]
    try:
        tokens = tokenize(source)
        statements = parse(tokens)
        assembly = codegen(statements)
    except CompileError as error:
        print(source, file=sys.stderr)
        print(" " * error.position + "^ " + str(error), file=sys.stderr)
        return 1

    print(assembly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
