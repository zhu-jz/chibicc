# Lesson 4: errors point to the source

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`cc5a6d978144bda90220bd10866c4fd908d07546`](https://github.com/rui314/chibicc/commit/cc5a6d978144bda90220bd10866c4fd908d07546),
“Improve error message.”

The `python-lessons` branch keeps the original C files intact. Previous
lessons and their explanations remain available in Git history:

| Lesson | Original commit | Python commit |
| --- | --- | --- |
| 1: one integer | `0522e2d` | `77c10f9` |
| 2: addition and subtraction | `bf7081f` | `d74a628` |
| 3: tokenization | `a1ab0ff` | `b92e285` |

## What changed

Previously, an error said only `invalid token` or `expected a number`.
Now it prints the original input and a caret at the relevant position:

```text
$ python3 python/main.py ' 12 + foo'
 12 + foo
      ^ invalid token

$ python3 python/main.py '1+'
1+
  ^ expected a number

$ python3 python/main.py '1 2'
1 2
  ^ expected '-'
```

The last message follows the original parser: after checking for `+`, it
requires `-`. These examples produce status 1 and write diagnostics to
standard error. They produce no assembly on standard output.

The original commit message shows `1+foo` with `expected a number`, but its
actual code tokenizes the entire input first and fails at `f` with
`invalid token`. This port follows the code.

## How source positions work

Each token now stores `position`, a zero-based character index in the
original input. Whitespace is still skipped, but its characters count
when recording a position. We do not strip the input.

For ` 12 + 34 `, the number 12 starts at position 1, the plus at 4, and
34 at 6. EOF is at position 9, after the trailing space. This allows a
missing-number diagnostic to point just past the input, even after spaces.

C already stored a pointer to the token's source text. The new C error
function subtracts the start-of-input pointer from the error pointer to
obtain the position. Python stores that position directly as an integer.

Read `main.py` in this order:

1. `Token.position` records where each token starts.
2. `CompileError` carries a position and an error message.
3. `tokenize()` raises it at an invalid character or an out-of-range literal.
4. `get_number()` and the operator check raise it at an unexpected token,
   including EOF.
5. `main()` catches it, prints the input, then prints `position` spaces
   followed by `^` and the message.

The source string stays local to `main()`. The original uses a global
`current_input`; using an exception to carry the position avoids needing
that global in this small Python version. Invalid argument counts still
produce a simple message because there is no single source input to mark.

Like the original, this is a basic character-offset display, not a
line-and-column renderer. Tabs, embedded newlines, and wide Unicode
characters can make the caret appear visually misaligned. Python counts
Unicode characters rather than C's byte offsets. We do not add terminal
width calculations or multiline formatting in this lesson.

## What the compiler accepts

The grammar and generated assembly are unchanged:

```text
number (('+' | '-') number)*
```

The `*` here means repetition in the grammar. The compiler accepts decimal
numbers and binary addition/subtraction, with whitespace between tokens.
It does not yet accept multiplication, division, parentheses, or unary
signs. For example, `-1` is rejected, while `0-1` produces a negative result.

The port retains its earlier intentional differences: a Python list of
tokens instead of a linked list, Unicode whitespace support, and explicit
literal limits of 0 through 2147483647. C stores `strtoul` results in an
`int` without checking that limit. The Python limit also keeps operands
suitable for signed 32-bit immediates in `add` and `sub`; intermediate
results use the 64-bit register. Assembly is buffered until parsing
succeeds, whereas C can emit partial assembly before a parser error.

## Run it in WSL

On x86-64 Linux with Python 3 and GCC installed (`python3` and
`build-essential` on Ubuntu), run from the repository root:

```sh
python3 python/main.py ' 12 + 34 - 5 ' > /tmp/chibicc-python-lesson4.s
cat /tmp/chibicc-python-lesson4.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson4 /tmp/chibicc-python-lesson4.s
/tmp/chibicc-python-lesson4
echo $?
```

The assembly is:

```asm
  .globl main
main:
  mov $12, %rax
  add $34, %rax
  sub $5, %rax
  ret
```

`.globl main` exposes the function to the linker; `main:` labels its entry.
AT&T syntax puts the source first: `$12` is a constant and `%rax` is a
register. Executing these instructions makes `%rax` hold 12, then 46,
then 41. `ret` returns to the C runtime. The executable does not print;
`echo $?` immediately afterward displays its exit status, **41**.

An `int` result uses `%eax`, the low 32 bits of `%rax`, and Linux exposes
the low eight bits as the exit status. Thus `0-1` exits with 255. Use an
ordinary interactive shell for the example; `set -e` stops scripts on
nonzero statuses. The compiler's successful status is independently 0.

Python emits the assembly without `eval()` or wrapping the C compiler.
GCC assembles and links it with the C runtime. `-static` follows the original
tests; `-Wl,-z,noexecstack` marks the stack non-executable.

## Tests and stopping point

```sh
python3 python/test.py
```

Tests verify exact diagnostic text and caret placement for tokenizer and
parser errors, missing operands at EOF, leading/trailing whitespace, empty
input, and out-of-range literals. They also check token positions and retain
all 17 valid assembly/executable cases from lesson 3, including all four
original upstream tests. Build artifacts use temporary directories.

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The complete
notice remains in `LICENSE` here and in the repository root; this port
uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
