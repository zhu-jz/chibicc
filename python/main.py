"""Lesson 132: Integer literal suffixes and types.

Based on chibicc commit aaf10459d93fb6c0f4539cb792c02a8d15cb0299.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import sys

from codegen import codegen
from common import CompileError
from parse import parse
from tokenizer import read_file, tokenize


def usage(status):
    print("chibicc (Python): python3 python/main.py [ -o <path> ] <file>", file=sys.stderr)
    raise SystemExit(status)


def parse_args(arguments):
    input_path = None
    output_path = None
    position = 0
    while position < len(arguments):
        argument = arguments[position]
        if argument == "--help":
            usage(0)
        if argument == "-o":
            position += 1
            if position == len(arguments):
                usage(1)
            output_path = arguments[position]
        elif argument.startswith("-o"):
            output_path = argument[2:]
        elif argument.startswith("-") and argument != "-":
            raise CompileError(None, f"unknown argument: {argument}")
        else:
            input_path = argument
        position += 1
    if input_path is None:
        raise CompileError(None, "no input files")
    return input_path, output_path


def write_output(path, assembly):
    text = assembly + ("\n" if assembly else "")
    if path is None or path == "-":
        sys.stdout.write(text)
        return
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(text)
    except OSError as error:
        raise CompileError(None, f"cannot open output file: {path}: {error.strerror}") from None


def main():
    try:
        filename, output_path = parse_args(sys.argv[1:])
        source = read_file(filename)
        tokens = tokenize(source)
        program = parse(tokens)
        assembly = codegen(program)
        escaped_filename = filename.replace("\\", "\\\\").replace('"', '\\"')
        assembly = f'.file 1 "{escaped_filename}"' + ("\n" + assembly if assembly else "")
        write_output(output_path, assembly)
    except CompileError as error:
        if error.position is None:
            print(error, file=sys.stderr)
        else:
            position = error.position
            line_start = source.rfind("\n", 0, position) + 1
            line_end = source.find("\n", position)
            if line_end == -1:
                line_end = len(source)
            line_number = error.line_no or source.count("\n", 0, line_start) + 1
            prefix = f"{filename}:{line_number}: "
            print(prefix + source[line_start:line_end], file=sys.stderr)
            print(" " * (len(prefix) + position - line_start) + "^ " + str(error),
                  file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
