# Lesson 3: a tokenizer handles whitespace

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`a1ab0ff26f23c82f15180051204eeb6279747c9a`](https://github.com/rui314/chibicc/commit/a1ab0ff26f23c82f15180051204eeb6279747c9a),
“Add a tokenizer to allow space characters between tokens.”

The `python-lessons` branch retains the original C files unchanged.
Earlier lessons and explanations remain in Git history:

| Lesson | Original commit | Python commit |
| --- | --- | --- |
| 1: one integer | `0522e2d` | `77c10f9` |
| 2: addition and subtraction | `bf7081f` | `d74a628` |

## Why tokenize?

Previously, the compiler read raw characters while generating instructions.
Number conversion skipped leading spaces, but operator reading did not:
`5+ 20-4` worked while `5 +20-4` failed.

Now `tokenize()` scans the entire input first. It skips whitespace wherever
it appears between tokens and produces a list of meaningful pieces:

```text
Input:   " 12 + 34 - 5 "
Tokens:  NUM(12), PUNCT(+), NUM(34), PUNCT(-), NUM(5), EOF
```

A token has a `kind`, its original `text`, and a numeric `value` used only
for number tokens. `NUM` represents consecutive ASCII digits; `PUNCT`
represents `+` or `-`. `EOF` marks the end of input, even though the input
is a command-line string rather than a file.

The scanner advances a character index. For digits, it consumes the whole
number; for punctuation, one character. Whitespace produces no token.
Anything else raises `invalid token`.

Whitespace separates tokens; it does not join numbers. Thus `1 2` becomes
two number tokens and is rejected, rather than becoming the number 12.

## Read the parser and assembly

After tokenization, `main()` works only with tokens. Its `position` is now
an index into the token list, not into the source string:

1. Require a number using `get_number()` and emit `mov`.
2. Until EOF, read `+` or `-`, then require another number.
3. Emit `add` or `sub` and advance by two tokens.
4. Emit `ret`.

The accepted grammar is:

```text
number (('+' | '-') number)*
```

Here `*` means the parenthesized part may repeat zero or more times; it
is grammar notation, not an operator supported by our compiler.

For ` 12 + 34 - 5 `, generated assembly is:

```asm
  .globl main
main:
  mov $12, %rax
  add $34, %rax
  sub $5, %rax
  ret
```

`.globl main` exposes the function to the linker and `main:` labels its
entry. AT&T assembly syntax puts the source first: `$12` is an immediate
constant and `%rax` is a register. When the executable runs, `%rax` holds
12, then 46, then 41. `ret` returns to the C runtime, which uses `main`'s
return value as the process exit status. Python emits instructions; it
does not evaluate the arithmetic or wrap the C compiler.

This remains a left-to-right compiler for addition and subtraction. There
is no syntax tree, multiplication, division, or parenthesized expression.
Errors are simple messages, without source locations or caret displays.

## A behavior change in the original commit

Previously, `strtol` happened to accept a sign as part of reading a number.
The new tokenizer always makes `+` and `-` separate punctuation tokens.
This commit's parser requires a number first and after each operator.
Consequently, `-1`, `+42`, `1+-2`, and `1--2` are now rejected. This follows
the original commit; it is not a Python-specific restriction.

You can still produce a negative result with `0-1`. Linux exposes only the
low eight bits of a normal exit status, so that program exits with 255.
Likewise, `255+2` exits with 1. An `int` function result uses `%eax`, the
low 32 bits of `%rax`.

## Python/C differences

- C stores tokens in a linked list. Python uses a standard list of simple
  dataclass objects and advances an index instead of following `next`.
- Python stores the token's text directly instead of a C pointer and length.
  Operator comparisons use normal string equality. The operator check is
  inline; `get_number()` performs the same kind check as the original helper.
- Python's `isspace()` also accepts Unicode whitespace. Numbers deliberately
  use ASCII digits, matching this lesson's decimal source syntax.
- We explicitly reject literals greater than 2147483647. This retains the
  previous lesson's range check, with signs now handled as punctuation.
  The original stores `strtoul`'s result in an `int` without a range check;
  out-of-range conversions are not portable. The bound also keeps literals
  suitable for the signed 32-bit immediate forms of `add` and `sub`.
  Intermediate results are computed in the 64-bit register.
- We buffer assembly until parsing succeeds. Errors go to standard error
  and leave standard output empty; C can print partial assembly on parser
  errors. Python integer conversion failures are also reported as errors.

## Run it in WSL

Use x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu). From the repository root, run these commands individually:

```sh
python3 python/main.py ' 12 + 34 - 5 ' > /tmp/chibicc-python-lesson3.s
cat /tmp/chibicc-python-lesson3.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson3 /tmp/chibicc-python-lesson3.s
/tmp/chibicc-python-lesson3
echo $?
```

The shell's `echo` prints **41**. The executable prints nothing itself.
Run `echo $?` immediately after the executable to see its exit status.
Use an ordinary interactive shell: `set -e` would stop a script on the
nonzero status. The compiler's own successful exit status is 0.

GCC assembles and links our assembly with the C runtime. `-static` follows
the original tests. `-Wl,-z,noexecstack` marks the stack non-executable
without adding assembly directives to this lesson.

## Tests

```sh
python3 python/test.py
```

Tests inspect token boundaries and EOF, check exact generated assembly,
assemble and link it with GCC, and run each valid program to check its
exit status. They include all four original tests through this commit:
`0`, `42`, `5+20-4`, and ` 12 + 34 - 5 `.

Additional cases cover spaces before operators, tabs and newlines, Unicode
whitespace, leading zeroes, negative results, exit-status truncation,
literal limits, missing operands, adjacent numbers, and unsupported syntax.
Signed-literal cases from the previous lesson now correctly expect errors.
Temporary executable and assembly files are automatically cleaned up.

## Attribution and stopping point

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full
original notice remains in `LICENSE` here and at the repository root.
This port uses the same MIT license.

Stop after this lesson. Implement the next original commit only after an
explicit confirmation that this lesson is understood and you are ready.
