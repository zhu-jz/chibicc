"""Lesson 8: compose the compiler from separate modules.

Based on chibicc commit 725badfb494544b7c7f1d4c4690b9bc033c6d051.
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
        node = parse(tokens)
        assembly = codegen(node)
    except CompileError as error:
        print(source, file=sys.stderr)
        print(" " * error.position + "^ " + str(error), file=sys.stderr)
        return 1

    print(assembly)
    return 0


if __name__ == "__main__":
    sys.exit(main())
