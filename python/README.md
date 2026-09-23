# Lesson 6: unary plus and minus

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`bf9ab52860c1cbbeeca40df515468f42300ff429`](https://github.com/rui314/chibicc/commit/bf9ab52860c1cbbeeca40df515468f42300ff429),
“Add unary plus and minus.” The `python-lessons` branch retains the
original C files unchanged. Earlier Python lessons and explanations remain
in Git history, ending with lesson 5 at Python commit `23d90e1`.

## What changed

The previous parser recognized `+` and `-` only between expressions. Now it
also accepts them before an expression:

```text
-10+20      → 10
- -10       → 10
- - +10     → 10
1--2        → 3
2*-(3+4)    → -14
```

The source still becomes tokens, then a tree, then x86-64 Linux assembly.
No arithmetic expression is evaluated using Python `eval()` or a wrapped
C compiler.

## Read the parser

The grammar now has a `unary` level between `mul` and `primary`:

```text
expr    = mul (("+" | "-") mul)*
mul     = unary (("*" | "/") unary)*
unary   = ("+" | "-") unary | primary
primary = "(" expr ")" | number
```

Outside quotes, `*` means repetition and `|` means a choice. Each function
returns a tree node and the index of the next unconsumed token. Because
`mul()` calls `unary()`, `-3*4` groups as `(-3)*4`. Parentheses still call
`expr()` so `-(3+4)` negates the entire sum.

For unary plus, `unary()` simply returns the next unary expression: `+10`
has the same tree as `10`. For unary minus, it wraps the next unary
expression in a `NEG` node. Recursive calls allow signs to chain:
`- - +10` becomes `NEG(NEG(NUM(10)))`. For `1--2`, the first minus is
binary subtraction in `expr()` and the second is unary negation in `unary()`.

The C commit adds a unary node constructor. This Python port uses the
existing `Node` dataclass with `kind="NEG"` and the operand in `lhs`.
The `rhs` field remains unused for that node. This keeps the tree shapes
close to the original C code without extra class types.

## Read the generated assembly

A number still emits `mov` into `%rax`. A `NEG` node first emits its
operand, then `neg %rax`. For `- - +10`, the compiler emits:

```asm
  .globl main
main:
  mov $10, %rax
  neg %rax
  neg %rax
  ret
```

The first `neg` changes 10 to -10. The second changes -10 back to 10.
Unary plus adds no machine instruction. Existing binary operators still
compute their right side first, save it with `push %rax`, compute the left
side, restore the right with `pop %rdi`, and perform the operation. Every
push is balanced by a pop before `ret`.

`.globl main` exposes `main` to the linker, and `main:` marks its entry.
`%rax` holds the result. GNU assembler AT&T syntax puts the source before
the destination; `$10` is an immediate constant. `ret` returns to the C
runtime. The program prints nothing. Linux exposes the low eight bits of
the return value as its exit status, so a result of -14 is reported as 242.

## Run it in WSL

On x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py '- - +10' > /tmp/chibicc-python-lesson6.s
cat /tmp/chibicc-python-lesson6.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson6 /tmp/chibicc-python-lesson6.s
/tmp/chibicc-python-lesson6
echo $?
```

The last command prints **10**. Run `echo $?` immediately after the
executable: it shows the preceding program's exit status. In a shell script,
`set -e` would stop on a nonzero exit status. The compiler's own successful
status is independently 0. GCC assembles and links our generated code with
the C runtime; `-static` follows the original tests and
`-Wl,-z,noexecstack` marks the stack non-executable.

## Scope and Python/C differences

The port retains the existing 0 through 2147483647 limit on each numeric
token. Thus `-2147483647` works: the parser negates a valid positive
literal. `-2147483648` still fails because its unsigned digit token is
2147483648, outside that limit. The original C compiler stores an unchecked
`strtoul` result in an `int`, so behavior beyond that type's range is not
portable. The port reports the error explicitly, with a caret.

Python uses a token list and dataclass tree nodes instead of C linked lists
and structs. It uses an integer token index instead of C pointer output
parameters. Source positions count Python characters instead of C bytes;
Unicode whitespace is accepted, and tabs or wide characters may make the
basic caret display look misaligned. The port buffers assembly until
compilation succeeds. Extremely long chains of unary signs can reach
Python's recursion limit; this lesson follows the original recursive
parser structure.

## Tests and stopping point

```sh
python3 python/test.py
```

The tests include all ten upstream assertions through this commit. They
check tree shape, exact `neg` assembly, and the executable's exit status for
single signs, chained signs, signed operands, grouping, and division.
They also retain the prior precedence, stack, tokenizer, and error-location
checks. Build artifacts use automatically cleaned temporary directories.

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full
notice remains in `LICENSE` here and in the repository root; this port
uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
