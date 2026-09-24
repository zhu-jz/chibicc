# Lesson 8: split the compiler into modules

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`725badfb494544b7c7f1d4c4690b9bc033c6d051`](https://github.com/rui314/chibicc/commit/725badfb494544b7c7f1d4c4690b9bc033c6d051),
“Split main.c into multiple small files.” It reorganizes the compiler
without adding syntax or changing generated assembly. Earlier lessons
remain in Git history; lesson 7 is Python commit `bbea860`.

## Where the code lives

| Original C file | Python file | Responsibility |
| --- | --- | --- |
| `chibicc.h` | `common.py` | Shared `Token`, `Node`, and `CompileError` types |
| `tokenize.c` | `tokenizer.py` | Convert source characters into tokens |
| `parse.c` | `parse.py` | Convert tokens into an expression tree |
| `codegen.c` | `codegen.py` | Convert the tree into assembly |
| `main.c` | `main.py` | Read the argument, run the stages, report errors |

Read `main.py` first. Its core is now just:

```python
tokens = tokenize(source)
node = parse(tokens)
assembly = codegen(node)
```

`parse()` is the new entry point for parsing. It calls `expr()` and checks
that the next token is EOF. Previously that final check lived in `main()`.
This means callers receive a complete parsed expression or an error.
The precedence functions below it retain their existing behavior.

`codegen()` is the entry point for assembly generation. It creates a fresh
`CodeGenerator`, whose assembly buffer and temporary stack depth belong to
that compilation. The generator still checks that pushes and pops balance.

Each module has one part of the compiler to explain. Changes to token
recognition belong in `tokenizer.py`, grammar rules in `parse.py`, and
machine instructions in `codegen.py`. Shared types in `common.py` avoid
circular imports between the stages.

## Python imports versus C headers

The original C commit moves shared declarations into `chibicc.h` and
updates the Makefile to compile and link all the `.c` files. In Python,
imports load the modules and make their definitions available. There is
no separate compiler build or Python equivalent of that Makefile change.

We use `tokenizer.py` instead of `tokenize.py` because Python already has
a standard-library module named `tokenize`. Shadowing it can break library
imports. `common.py` defines the shared classes rather than declaring C
structs and function prototypes. The command-line driver still catches
`CompileError` and prints caret diagnostics; this preserves the previous
Python exception approach without introducing C's global input pointer.

## Run it in WSL

Use x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu). From the repository root:

```sh
python3 python/main.py '1<2' > /tmp/chibicc-python-lesson8.s
cat /tmp/chibicc-python-lesson8.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson8 /tmp/chibicc-python-lesson8.s
/tmp/chibicc-python-lesson8
echo $?
```

The final command prints **1**, the true result of `1<2`. Quote expressions
so the shell does not interpret `<` or `>` as redirection. The executable
itself prints nothing; `echo $?` displays the preceding program's exit
status. Use an ordinary interactive shell: `set -e` would stop a script
on status 1. The compiler's own successful status is 0.

The output remains:

```asm
  .globl main
main:
  mov $2, %rax
  push %rax
  mov $1, %rax
  pop %rdi
  cmp %rdi, %rax
  setl %al
  movzb %al, %rax
  ret
```

`.globl main` exposes the function to the linker. `mov` loads each number;
`push` and `pop` preserve the right operand while computing the left.
`cmp` sets flags comparing the left in `%rax` with the right in `%rdi`.
`setl` puts the signed less-than result in `%al`, and `movzb` expands it to
exactly 0 or 1 in `%rax`. `ret` returns to the C runtime, which turns the
result into an exit status. GCC assembles and links this code; Python emits
it without `eval()` or invoking the original C compiler. `-static` follows
the original tests, and `-Wl,-z,noexecstack` marks the stack non-executable.

## Tests, existing limits, and attribution

```sh
python3 python/test.py
```

The existing tests now import the modules directly and use `parse()` for
tree checks. They still verify token positions, expression trees, exact
assembly, caret diagnostics, and 84 assembled-and-executed expressions,
including all 26 original assertions through this commit. This is a
refactoring lesson, so the previous behavior is the regression target.
Temporary build artifacts are cleaned up automatically.

The earlier intentional differences remain: Python token lists and
dataclasses, explicit numeric-token limits of 0 through 2147483647,
Unicode whitespace support, character indices instead of byte offsets,
and buffered assembly output. Unary minus is separate from the numeric
token, so `-2147483648` remains outside the literal policy. Intermediate
arithmetic uses 64-bit registers; normal exit statuses retain eight bits.
The basic caret display may misalign for tabs or wide characters, deep
trees can reach Python's recursion limit, and runtime division by zero
remains unchecked as in the original.

All implementation changes are in `python/`, on the `python-lessons`
branch. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed.
The full notice remains in `LICENSE` here and in the repository root.
This port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
