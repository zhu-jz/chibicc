# Lesson 1: an integer becomes an executable

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc). This lesson implements only
original commit [`0522e2d77e3ab82d3b80a5be8dbbdc8d4180561c`](https://github.com/rui314/chibicc/commit/0522e2d77e3ab82d3b80a5be8dbbdc8d4180561c),
“Compile an integer to an exectuable that exits with the given number”
(original title spelling).

The `python-lessons` branch starts from the existing repository checkout;
the original C files are retained unchanged. The Python implementation's
scope starts at the first original commit, regardless of the C checkout's
version. There is no tokenizer, expression parser, or later lesson here.

## Run it in WSL

Use an x86-64 Linux WSL terminal with Python 3 and GCC installed. On Ubuntu,
the prerequisite packages are `python3` and `build-essential`.
From the repository root, run these commands individually:

```sh
python3 python/main.py 42 > /tmp/chibicc-python-lesson1.s
cat /tmp/chibicc-python-lesson1.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson1 /tmp/chibicc-python-lesson1.s
/tmp/chibicc-python-lesson1
echo $?
```

The last command prints `42`. The executable itself prints nothing. Run
`echo $?` immediately after the executable: it reports the preceding
command's exit status. A shell using `set -e` will stop on status 42, so use
an ordinary interactive shell for this example.

GCC assembles our generated assembly and links it with the C runtime,
whose startup code calls `main`. Python performs the entire compilation
from the input integer to assembly; it does not invoke a C compiler or use
`eval()`. The test harness invokes GCC only to assemble and link the result.
`-static` follows the original test script. `-Wl,-z,noexecstack` tells the
linker that this program does not need an executable stack, keeping the
original four-line assembly output intact.

## Read the compiler and its output

Read `main.py` from top to bottom: check that there is exactly one argument,
convert it to an integer, emit assembly to standard output, and return zero
to indicate that compilation succeeded. Errors go to standard error and
produce no assembly.

For `42`, the output is:

```asm
  .globl main
main:
  mov $42, %rax
  ret
```

- `.globl main` makes the `main` symbol visible to the linker.
- `main:` labels the address at which the function starts.
- `mov $42, %rax` uses GNU assembler AT&T syntax: `$42` is an immediate
  constant, `%rax` is a register, and the source comes before the destination.
  `%rax` is the x86-64 integer return register; an `int` result uses its
  lower 32 bits (`%eax`). This instruction sets both appropriately.
- `ret` returns to the runtime caller using the return address on the stack.
  The runtime turns `main`'s return value into the process exit status.

No stack frame is needed because this function has no local variables and
calls no other functions. The compiler's successful exit status is `0`;
the generated executable's exit status is `42`. Those are separate programs.

## Intentional Python/C differences

The original uses `atoi`, which accepts an initial numeric prefix (`42abc`
becomes 42) and returns zero when there is no conversion (`abc`). This port
requires a complete decimal integer: optional surrounding whitespace,
optional sign, then ASCII digits. Malformed input is a compilation error.
Python's whitespace stripping also recognizes Unicode whitespace.

Python integers can exceed a C `int`. We explicitly accept only
`-2147483648` through `2147483647`, matching the defined input range of
`atoi` with a 32-bit `int` on our target. C `atoi` overflow is undefined;
this port reports an error. Extremely long inputs may also hit Python's
integer conversion limit and are reported as errors.

Linux exposes only the low eight bits of the return value as a normal
process exit status. Thus `256` exits with status `0`, and `-1` exits with
status `255`. The assembly still contains the original integer.

## Tests

```sh
python3 python/test.py
```

The standard-library tests check the exact assembly, assemble and link it
with GCC, run the resulting executable, and check its exit status. They
cover the original `0` and `42` cases, signs, exit-status truncation, the
32-bit boundaries, and input errors. Build artifacts use a temporary
directory that is cleaned up automatically.

## Attribution and stopping point

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full
original notice is preserved in `LICENSE` alongside this port and in the
repository root. This port is distributed under the same MIT license.

Stop after this lesson. Implement the next original commit only after an
explicit confirmation that this lesson is understood and you are ready.
