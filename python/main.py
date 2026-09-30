"""Lesson 28: Arrays of arrays.

Based on chibicc commit 3ce1b2d067164f754dcb4216c193dc98e164b3ce.
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
        program = parse(tokens)
        assembly = codegen(program)
    except CompileError as error:
        if error.position is None:
            print(error, file=sys.stderr)
        else:
            print(source, file=sys.stderr)
            print(" " * error.position + "^ " + str(error), file=sys.stderr)
        return 1

    sys.stdout.write(assembly + ("\n" if assembly else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
