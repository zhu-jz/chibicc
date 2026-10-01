"""Lesson 155: Assemble output unless -S is given.

Based on chibicc commit 140b43358c33fb5e9f86789541dbca306bb64fcc.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import sys
import subprocess
from pathlib import Path
import tempfile

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
    opt_cc1 = False
    opt_trace = False
    opt_S = False
    position = 0
    while position < len(arguments):
        argument = arguments[position]
        if argument == "-S":
            opt_S = True
            position += 1
            continue
        if argument == "-cc1":
            opt_cc1 = True
            position += 1
            continue
        if argument == "-###":
            opt_trace = True
            position += 1
            continue
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
    return input_path, output_path, opt_cc1, opt_trace, opt_S


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


def cc1(filename, output_path):
    try:
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


def run_subprocess(command, trace):
    if trace:
        print(" ".join(command), file=sys.stderr)
    try:
        result = subprocess.run(command)
    except OSError as error:
        raise CompileError(None, f"exec failed: {command[0]}: {error.strerror}") from None
    return 0 if result.returncode == 0 else 1


def run_cc1(arguments, input_path, output_path, trace):
    command = [sys.executable, sys.argv[0], *arguments, "-cc1", input_path, "-o", output_path]
    return run_subprocess(command, trace)


def replace_extension(filename, extension):
    name = Path(filename).name
    dot = name.rfind(".")
    if dot >= 0:
        name = name[:dot]
    return name + extension


def main():
    try:
        filename, output_path, opt_cc1, opt_trace, opt_S = parse_args(sys.argv[1:])
        if opt_cc1:
            return cc1(filename, output_path)
        if output_path is None:
            output_path = replace_extension(filename, ".s" if opt_S else ".o")
        if opt_S:
            return run_cc1(sys.argv[1:], filename, output_path, opt_trace)
        with tempfile.TemporaryDirectory(prefix="chibicc-") as directory:
            assembly_path = str(Path(directory) / "input.s")
            status = run_cc1(sys.argv[1:], filename, assembly_path, opt_trace)
            if status:
                return status
            return run_subprocess(["as", "-c", assembly_path, "-o", output_path], opt_trace)
    except CompileError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
