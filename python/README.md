# Lesson 2: addition and subtraction

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
The current lesson implements original commit
[`bf7081fba7d8c6b1cd8a12eb329697a5481c604e`](https://github.com/rui314/chibicc/commit/bf7081fba7d8c6b1cd8a12eb329697a5481c604e),
“Add + and - operators.” It builds on lesson 1, original commit
`0522e2d77e3ab82d3b80a5be8dbbdc8d4180561c` (Python commit `77c10f9`).
The first lesson and its explanation remain available in Git history.

The `python-lessons` branch starts from the existing repository checkout.
The original C files remain unchanged; only `python/` implements the lessons.

## What changed

Previously, a single number produced one `mov` instruction. Now an input
such as `5+20-4` produces:

```asm
  .globl main
main:
  mov $5, %rax
  add $20, %rax
  sub $4, %rax
  ret
```

`.globl main` exposes the function to the linker, and `main:` marks its
starting address. GNU assembler AT&T syntax puts the source first: `$5`
is an immediate constant, and `%rax` is a register.

When the executable runs, `mov` sets `%rax` to 5, `add` increases it to 25,
and `sub` decreases it to 21. `ret` returns to the C runtime caller. An
`int` return value uses `%eax`, the low 32 bits of `%rax`; Linux exposes
the low eight bits as the process exit status. Thus `0-1` gives status 255,
and `255+2` gives status 1. The program itself prints nothing.

The compiler does not calculate the expression's result in Python. It
converts each number separately and emits instructions that perform the
arithmetic when the executable runs. There is no `eval()` or C compiler
wrapper.

## How the Python code follows the C code

In `main.py`, `position` is the index of the next unconsumed character.
It plays the role of the original C pointer `p`.

1. `read_number(source, position)` returns a number and the new position,
   mirroring the number conversion and pointer update of `strtol(p, &p, 10)`.
2. Emit `mov` for the first number.
3. While characters remain, read `+` or `-`, advance past it, read the
   next number, and emit `add` or `sub`.
4. Emit `ret` after the entire input has been consumed.

For `5+20-4`, the first number leaves `position` at index 1 (`+`). The first
loop iteration reads 20 and leaves it at index 4 (`-`). The second reads
4 and reaches index 6, the end of the string.

The loop processes operations from left to right: `10-3-2` means
`(10-3)-2`, giving 5. There is no tokenizer, syntax tree, multiplication,
division, or parentheses in this lesson.

## Run it in WSL

Use an x86-64 Linux WSL terminal with Python 3 and GCC installed
(`python3` and `build-essential` on Ubuntu). From the repository root,
run these commands individually:

```sh
python3 python/main.py '5+20-4' > /tmp/chibicc-python-lesson2.s
cat /tmp/chibicc-python-lesson2.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson2 /tmp/chibicc-python-lesson2.s
/tmp/chibicc-python-lesson2
echo $?
```

The last command prints `21`. The shell stores the executable's exit
status in `$?`, and `echo` makes it visible. Run `echo $?` immediately after
the executable. Use an ordinary interactive shell: `set -e` would stop a
script when the executable returns a nonzero status.

GCC assembles the generated assembly and links it with the C runtime,
whose startup code calls `main`. `-static` follows the original tests;
`-Wl,-z,noexecstack` marks the stack as non-executable without adding
assembly directives to this lesson. The compiler's own success status
is 0, independently of the generated program's result.

## Input behavior and intentional differences

Like the original `strtol`, `read_number` accepts whitespace before a
number and an optional sign. Thus `5+ 20-4`, `1+-2`, and `1--2` work. This
is number-conversion behavior, not a general unary-expression parser.
Spaces before an operator, as in `5 +20`, are still rejected. We have not
added general support for whitespace between tokens.

We retain lesson 1's stripping of surrounding whitespace; unlike the
original C loop, this accepts trailing whitespace. Python's whitespace
handling also recognizes Unicode whitespace; digits must be ASCII.

Unlike C `strtol` calls with no conversion checks, this port rejects
missing numbers: for example, `1+` is an error rather than silently adding
zero. Unknown characters are also errors. We collect assembly lines and
print them only after successful parsing, so errors leave standard output
empty. The C version can print partial assembly before detecting an error.

The original commit changes from `atoi` (32-bit `int` on our target) to
`strtol` (64-bit `long`). This port deliberately retains lesson 1's signed
32-bit limit for each literal: -2147483648 through 2147483647. The immediate
forms of `add` and `sub` on `%rax` take signed 32-bit constants; accepting
arbitrary 64-bit operands would require more instructions or risk assembler
errors. The original compiler does not check that restriction. Our limit
applies to each literal, not to intermediate results in the 64-bit register.
Python integer-conversion errors are also reported as compilation errors.

## Tests

```sh
python3 python/test.py
```

The standard-library tests check exact assembly, assemble and link it with
GCC, run it, and check the exit status. They retain lesson 1's valid cases
and add the original `5+20-4` test, consecutive subtraction, negative and
wrapping results, signed operands, and immediate boundaries. Invalid-input
tests cover missing operands, unsupported syntax, whitespace before an
operator, and out-of-range literals. Build artifacts live in an automatically
cleaned temporary directory.

## Attribution and stopping point

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full
original notice is preserved in `LICENSE` alongside this port and in the
repository root. This port is distributed under the same MIT license.

Stop after this lesson. Implement the next original commit only after an
explicit confirmation that this lesson is understood and you are ready.
