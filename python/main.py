"""Lesson 21: scale pointer arithmetic using expression types.

Based on chibicc commit a6bc4ab101c20b6398fd6bbfe124665bb7db5d25.
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

    print(assembly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
