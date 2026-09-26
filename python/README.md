# Lesson 14: null statements

This educational Python port implements original chibicc commit
[`ff8912c68e877744f8b15070e098af786e7bd296`](https://github.com/rui314/chibicc/commit/ff8912c68e877744f8b15070e098af786e7bd296),
“Add null statement.” Earlier lessons remain in Git history; lesson 13
is Python commit `bd4eac4`.

## What changed

A semicolon by itself is now a valid statement that does nothing:

```c
{ ;;; return 5; }
```

The three initial semicolons are three null statements. The program returns
5. Extra semicolons also work after an expression or block:

```c
{ a=3;; { a=a+2; }; return a;; }
```

This returns 5. The semicolon after the closing inner brace is a separate
null statement, rather than part of the block's syntax.

## Parser and assembly

The expression-statement rule changes from `expr ";"` to:

```text
expr-stmt = expr? ";"
```

The `?` means the expression is optional. In `Parser.expr_stmt()`, if the
current token is `;`, the parser consumes it and returns `Node("BLOCK")`
with an empty child list. Otherwise, it parses an expression and requires
a terminating semicolon as before.

The original C commit also represents a null statement as an empty block.
Python's dataclass gives it its own empty list instead of C's null linked-list
pointer. The existing block generator iterates over that list, so a null
statement emits no instructions. No new assembly instruction or node kind
is needed.

For `{ ;;; return 5; }`, the assembly is:

```asm
  .globl main
main:
  push %rbp
  mov %rsp, %rbp
  sub $0, %rsp
  mov $5, %rax
  jmp .L.return
.L.return:
  mov %rbp, %rsp
  pop %rbp
  ret
```

The prologue establishes the stack frame; this program has no locals.
`mov $5, %rax` sets the result, the jump reaches the common epilogue, and
`ret` returns after restoring the caller's stack. There are no instructions
for the three null statements.

## Run it in WSL

With Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py '{ ;;; return 5; }' > /tmp/chibicc-python-lesson14.s
cat /tmp/chibicc-python-lesson14.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson14 /tmp/chibicc-python-lesson14.s
/tmp/chibicc-python-lesson14
echo $?
```

The last command prints **5**. The executable itself prints nothing;
`echo $?` immediately afterward displays its exit status. Quote the input
so the shell does not interpret its semicolons. Use an ordinary interactive
shell; `set -e` would stop a script on status 5.

GCC assembles and links our emitted code with the C runtime. `-static`
follows upstream tests and `-Wl,-z,noexecstack` marks the stack non-executable.
The Python compiler does not use `eval()` or invoke the original C compiler.

## Limits and tests

A return still requires an expression: `{ return; }` remains an error.
A null statement cannot fill in a missing arithmetic operand, so
`{ 1+; }` is also an error. A program containing only null statements sets
no result; tests check its assembly without assuming an exit status.

Outer braces are still required. Blocks still share function-wide locals,
and the parser retains the original behavior of ignoring tokens after the
first outer block. Earlier Python/C differences remain: lists and dataclasses,
explicit numeric-token bounds of 0 through 2147483647, Unicode whitespace,
character-based diagnostic positions, and buffered assembly output.
Variables are uninitialized until assigned; arithmetic uses 64-bit registers
and normal exit statuses expose eight bits.

```sh
python3 python/test.py
```

Tests cover the original `{ ;;; return 5; }` example, null-statement tree
shape, exact assembly showing no added instructions, extra semicolons after
expressions and blocks, and the existing error cases. All earlier valid
programs remain in the executable tests. Temporary artifacts are cleaned up.

All implementation changes are in `python/` on `python-lessons`; original
C files remain intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in `LICENSE` here and in the repository
root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
