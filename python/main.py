"""Lesson 41: Assembly line-output refactor.

Based on chibicc commit 7b8528f71c78a01e8ff41a76a83a320d1ef80e93.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import sys

from codegen import codegen
from common import CompileError
from parse import parse
from tokenizer import read_file, tokenize


def main():
    if len(sys.argv) != 2:
        print(f"{sys.argv[0]}: invalid number of arguments", file=sys.stderr)
        return 1

    filename = sys.argv[1]
    try:
        source = read_file(filename)
        tokens = tokenize(source)
        program = parse(tokens)
        assembly = codegen(program)
    except CompileError as error:
        if error.position is None:
            print(error, file=sys.stderr)
        else:
            position = error.position
            line_start = source.rfind("\n", 0, position) + 1
            line_end = source.find("\n", position)
            if line_end == -1:
                line_end = len(source)
            line_number = source.count("\n", 0, line_start) + 1
            prefix = f"{filename}:{line_number}: "
            print(prefix + source[line_start:line_end], file=sys.stderr)
            print(" " * (len(prefix) + position - line_start) + "^ " + str(error),
                  file=sys.stderr)
        return 1

    sys.stdout.write(assembly + ("\n" if assembly else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
