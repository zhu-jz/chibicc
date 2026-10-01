"""Lesson 292: Choose dependency targets with -MT.

Based on chibicc commit db850f37a2a284bf18cea427e4676a22d83d04b8.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import sys
import subprocess
from pathlib import Path
import tempfile
import glob
from typing import NoReturn

from codegen import codegen
from common import CompileError, format_diagnostic
from parse import parse
from preprocess import preprocess, init_macros, define_macro, undef_macro, search_include_paths
from tokenizer import tokenize_file


def usage(status) -> NoReturn:
    print("chibicc (Python): python3 python/main.py [ -o <path> ] <file>", file=sys.stderr)
    raise SystemExit(status)


def add_default_include_paths(argv0, include_paths):
    include_paths.extend([
        str(Path(argv0).parent / "include"),
        "/usr/local/include",
        "/usr/include/x86_64-linux-gnu",
        "/usr/include",
    ])


def parse_args(arguments):
    input_paths = []
    include_paths = []
    idirafter = []
    forced_includes = []
    output_path = None
    base_file = None
    cc1_output = None
    opt_cc1 = False
    opt_trace = False
    opt_S = False
    opt_c = False
    opt_E = False
    opt_M = False
    opt_MF = None
    opt_MP = False
    opt_MT = None
    opt_fcommon = True
    opt_x = None
    ld_extra_args = []
    position = 0
    while position < len(arguments):
        if arguments[position] in ("-o", "-I", "-D", "-U", "-idirafter", "-include", "-x", "-MF", "-MT", "-cc1-input", "-cc1-output"):
            position += 1
            if position == len(arguments):
                usage(1)
            if arguments[position - 1] == "-cc1-input":
                base_file = arguments[position]
        position += 1
    macros = init_macros(base_file or "-")
    position = 0
    while position < len(arguments):
        argument = arguments[position]
        if argument == "-MT":
            target = arguments[position + 1]
            opt_MT = target if opt_MT is None else opt_MT + " " + target
            position += 2
            continue
        if argument == "-MP":
            opt_MP = True
            position += 1
            continue
        if argument == "-MF":
            opt_MF = arguments[position + 1]
            position += 2
            continue
        if argument == "-M":
            opt_M = True
            position += 1
            continue
        if argument == "-hashmap-test":
            from hashmap import hashmap_test
            hashmap_test()
            raise SystemExit(0)
        if argument == "-s":
            ld_extra_args.append(argument)
            position += 1
            continue
        if argument.startswith("-l"):
            input_paths.append(argument)
            position += 1
            continue
        if argument.startswith("-x"):
            language = argument[2:]
            if argument == "-x":
                position += 1
                language = arguments[position]
            opt_x = parse_opt_x(language)
            position += 1
            continue
        if argument == "-include":
            forced_includes.append(arguments[position + 1])
            position += 2
            continue
        if argument in ("-fcommon", "-fno-common"):
            opt_fcommon = argument == "-fcommon"
            position += 1
            continue
        if argument == "-idirafter":
            # This original patch stores the option itself, not its argument.
            idirafter.append(argument)
            position += 2
            continue
        if argument.startswith("-U"):
            name = argument[2:]
            if argument == "-U":
                position += 1
                name = arguments[position]
            undef_macro(macros, name)
            position += 1
            continue
        if argument.startswith("-D"):
            definition = argument[2:]
            if argument == "-D":
                position += 1
                definition = arguments[position]
            name, separator, value = definition.partition("=")
            define_macro(macros, name, value if separator else "1")
            position += 1
            continue
        if argument == "-E":
            opt_E = True
            position += 1
            continue
        if argument == "-c":
            opt_c = True
            position += 1
            continue
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
        if argument in ("-cc1-input", "-cc1-output"):
            position += 1
            if argument == "-cc1-input":
                base_file = arguments[position]
            else:
                cc1_output = arguments[position]
            position += 1
            continue
        if argument == "-o":
            position += 1
            if position == len(arguments):
                usage(1)
            output_path = arguments[position]
        elif argument.startswith("-o"):
            output_path = argument[2:]
        elif argument.startswith("-I"):
            include_paths.append(argument[2:])
        elif (argument.startswith(("-O", "-W", "-g", "-std=")) or
              argument in ("-ffreestanding", "-fno-builtin", "-fno-omit-frame-pointer",
                           "-fno-stack-protector", "-fno-strict-aliasing", "-m64",
                           "-mno-red-zone", "-w")):
            pass  # Compatibility flags accepted by this original driver step.
        elif argument.startswith("-") and argument != "-":
            raise CompileError(None, f"unknown argument: {argument}")
        else:
            input_paths.append(argument)
        position += 1
    include_paths.extend(idirafter)
    if not input_paths:
        raise CompileError(None, "no input files")
    if opt_E:
        opt_x = "C"
    return input_paths, output_path, opt_cc1, opt_trace, opt_S, opt_c, opt_E, base_file, cc1_output, include_paths, macros, opt_fcommon, forced_includes, opt_x, ld_extra_args, opt_M, opt_MF, opt_MP, opt_MT


def parse_opt_x(language):
    if language not in ("c", "assembler", "none"):
        raise CompileError(None, f"<command line>: unknown argument for -x: {language}")
    return {"c": "C", "assembler": "ASM", "none": None}[language]


def get_file_type(filename, opt_x):
    if opt_x is not None:
        return opt_x
    if filename.endswith(".a"):
        return "AR"
    if filename.endswith(".so"):
        return "DSO"
    if filename.endswith(".o"):
        return "OBJ"
    if filename.endswith(".c"):
        return "C"
    if filename.endswith(".s"):
        return "ASM"
    raise CompileError(None, f"<command line>: unknown file extension: {filename}")


def write_output(path, assembly):
    text = assembly if assembly.endswith("\n") else assembly + ("\n" if assembly else "")
    if path is None or path == "-":
        sys.stdout.write(text)
        return
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as output_file:
            output_file.write(text)
    except OSError as error:
        raise CompileError(None, f"cannot open output file: {path}: {error.strerror}") from None


def print_tokens(tokens, output_path):
    parts = []
    for index, token in enumerate(tokens):
        if token.kind == "EOF":
            break
        if index > 0 and token.at_bol:
            parts.append("\n")
        if token.has_space and not token.at_bol:
            parts.append(" ")
        parts.append(token.text)
    write_output(output_path, "".join(parts) + "\n")


def print_dependencies(filename, files, output_path, phony=False, target=None):
    text = (target if target is not None else replace_extension(filename, ".o")) + ":"
    for file in files:
        text += " \\\n  " + file.name
    text += "\n\n"
    if phony:
        for file in files[1:]:
            text += file.name + ":\n\n"
    write_output(output_path, text)


def cc1(filename, output_path, opt_E=False, opt_o=None, include_paths=(), macros=None, fcommon=True, forced_includes=(), opt_M=False, opt_MF=None, opt_MP=False, opt_MT=None):
    files = []
    try:
        tokens = []
        for header in forced_includes:
            path = header if Path(header).exists() else search_include_paths(header, include_paths)
            if path is None:
                raise CompileError(None, f"-include: {header}: No such file or directory")
            tokens.extend(tokenize_file(path, files)[:-1])
        tokens.extend(tokenize_file(filename, files))
        if macros is None:
            macros = init_macros(filename)
        tokens = preprocess(tokens, files, include_paths, macros)
        if opt_M:
            print_dependencies(filename, files, opt_MF if opt_MF is not None else opt_o, opt_MP, opt_MT)
            return 0
        if opt_E:
            print_tokens(tokens, opt_o)
            return 0
        program = parse(tokens)
        # Finish all code generation in memory before opening the destination.
        assembly = codegen(program, files, fcommon)
        write_output(output_path, assembly)
    except CompileError as error:
        if error.position is None:
            print(error, file=sys.stderr)
        else:
            file = error.file or files[0]
            print(format_diagnostic(file, error.position, str(error), error.line_no), file=sys.stderr)
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
    command = [sys.executable, sys.argv[0], *arguments, "-cc1",
               "-cc1-input", input_path]
    if output_path is not None:
        command.extend(("-cc1-output", output_path))
    return run_subprocess(command, trace)


def replace_extension(filename, extension):
    name = Path(filename).name
    dot = name.rfind(".")
    if dot >= 0:
        name = name[:dot]
    return name + extension


def find_library_path():
    for directory in ("/usr/lib/x86_64-linux-gnu", "/usr/lib64"):
        if (Path(directory) / "crti.o").exists():
            return directory
    raise CompileError(None, "library path is not found")


def find_gcc_library_path():
    for pattern in ("/usr/lib/gcc/x86_64-linux-gnu/*/crtbegin.o",
                    "/usr/lib/gcc/x86_64-pc-linux-gnu/*/crtbegin.o",
                    "/usr/lib/gcc/x86_64-redhat-linux/*/crtbegin.o"):
        matches = sorted(glob.glob(pattern))
        if matches:
            return str(Path(matches[-1]).parent)
    raise CompileError(None, "gcc library path is not found")


def run_linker(inputs, output, trace, extra_args=()):
    library = find_library_path()
    gcc_library = find_gcc_library_path()
    command = ["ld", "-o", output, "-m", "elf_x86_64", "-dynamic-linker",
               "/lib64/ld-linux-x86-64.so.2", f"{library}/crt1.o", f"{library}/crti.o",
               f"{gcc_library}/crtbegin.o", f"-L{gcc_library}", f"-L{library}", f"-L{library}/..",
               "-L/usr/lib64", "-L/lib64", "-L/usr/lib/x86_64-linux-gnu",
               "-L/usr/lib/x86_64-pc-linux-gnu", "-L/usr/lib/x86_64-redhat-linux",
               "-L/usr/lib", "-L/lib", *extra_args, *inputs, "-lc", "-lgcc", "--as-needed", "-lgcc_s",
               "--no-as-needed", f"{gcc_library}/crtend.o", f"{library}/crtn.o"]
    return run_subprocess(command, trace)


def main():
    try:
        (inputs, opt_o, opt_cc1, opt_trace, opt_S, opt_c, opt_E,
         base_file, cc1_output, include_paths, macros, opt_fcommon, forced_includes, opt_x, ld_extra_args, opt_M, opt_MF, opt_MP, opt_MT) = parse_args(sys.argv[1:])
        if opt_cc1:
            add_default_include_paths(sys.argv[0], include_paths)
            if base_file is None:
                raise CompileError(None, "-cc1 requires -cc1-input")
            return cc1(base_file, cc1_output, opt_E, opt_o, include_paths, macros, opt_fcommon, forced_includes, opt_M, opt_MF, opt_MP, opt_MT)
        if len(inputs) > 1 and opt_o is not None and (opt_c or opt_S or opt_E):
            raise CompileError(None, "cannot specify '-o' with '-c,' '-S' or '-E' with multiple files")
        linker_inputs = []
        with tempfile.TemporaryDirectory(prefix="chibicc-") as directory:
            for index, filename in enumerate(inputs):
                if filename.startswith("-l"):
                    linker_inputs.append(filename)
                    continue
                output_path = opt_o if opt_o is not None else replace_extension(filename, ".s" if opt_S else ".o")
                file_type = get_file_type(filename, opt_x)
                if file_type in ("OBJ", "AR", "DSO"):
                    linker_inputs.append(filename)
                    continue
                if file_type == "ASM":
                    if not opt_S:
                        status = run_subprocess(["as", "-c", filename, "-o", output_path], opt_trace)
                        if status:
                            return status
                    continue
                if opt_E or opt_M:
                    status = run_cc1(sys.argv[1:], filename, None, opt_trace)
                elif opt_S:
                    status = run_cc1(sys.argv[1:], filename, output_path, opt_trace)
                else:
                    assembly_path = str(Path(directory) / f"{index}.s")
                    object_path = output_path if opt_c else str(Path(directory) / f"{index}.o")
                    status = run_cc1(sys.argv[1:], filename, assembly_path, opt_trace)
                    if not status:
                        status = run_subprocess(["as", "-c", assembly_path, "-o", object_path], opt_trace)
                    if not opt_c:
                        linker_inputs.append(object_path)
                if status:
                    return status
            if linker_inputs:
                return run_linker(linker_inputs, opt_o if opt_o is not None else "a.out", opt_trace, ld_extra_args)
        return 0
    except CompileError as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
