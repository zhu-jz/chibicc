# Lesson 9: expression statements and semicolons

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`76cae0ad05b6ba3e3e927b2b749ccddda23f0c51`](https://github.com/rui314/chibicc/commit/76cae0ad05b6ba3e3e927b2b749ccddda23f0c51),
“Accept multiple statements separated by semicolons.” Earlier lessons
remain in Git history; lesson 8 is Python commit `2240456`.

## What changed

A program now consists of expression statements. Every expression must
end with a semicolon, including the last one:

```text
42;                 → 42
1; 2; 3;            → 3
1+2; 3*(4+5);       → 27
```

The executable evaluates statements in source order. Each result is left
in `%rax`; the next statement overwrites it. The final `ret` therefore
returns the last statement's value. This is the behavior of this early
compiler stage, not a general rule that C functions implicitly return
the value of their last expression statement.

`42` alone now reports `expected ';'`. This syntax change follows the
original commit, which adds semicolons to every existing test.

## Read the parser and generator

The program grammar gains three rules above the existing expression rules:

```text
program   = stmt*
stmt      = expr-stmt
expr-stmt = expr ";"
```

The `*` here means zero or more repetitions. The rules for precedence,
comparisons, unary signs, and parentheses are unchanged.

In `parse.py`, `expr_stmt()` parses one expression, requires `;`, and wraps
the tree in `Node("EXPR_STMT", lhs=expression)`. This distinguishes an
expression used as a statement from expressions nested inside arithmetic.
`stmt()` calls `expr_stmt()`. `parse()` repeats until EOF and returns the
statements in a Python list. For `1; 2+3;`, the structure is:

```text
[
  EXPR_STMT(NUM(1)),
  EXPR_STMT(ADD(NUM(2), NUM(3)))
]
```

The original C commit adds a `next` pointer to link statements. Python's
standard list serves that purpose, so our `Node` dataclass needs no extra
field. The expression itself still lives in `lhs`, matching C.

In `codegen.py`, `gen_stmt()` calls `gen_expr()` for an expression statement.
`generate()` walks the statement list, checks that temporary stack depth
is zero after each statement, then emits one `ret` at the end. Existing
expression generation emits every statement; it does not discard earlier
statements just because only the last result is returned.

`main.py` still connects the stages:

```python
tokens = tokenize(source)
statements = parse(tokens)
assembly = codegen(statements)
```

## Run it in WSL

Use x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu). From the repository root:

```sh
python3 python/main.py '1; 2; 3;' > /tmp/chibicc-python-lesson9.s
cat /tmp/chibicc-python-lesson9.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson9 /tmp/chibicc-python-lesson9.s
/tmp/chibicc-python-lesson9
echo $?
```

The last command prints **3**. Quote the source because the shell also uses
semicolons to separate commands. The executable itself prints nothing;
`echo $?` immediately afterward displays its exit status. Use an ordinary
interactive shell: `set -e` would stop a script on status 3. The compiler's
own successful status is 0.

The generated assembly is:

```asm
  .globl main
main:
  mov $1, %rax
  mov $2, %rax
  mov $3, %rax
  ret
```

`.globl main` exposes the function to the linker and `main:` labels its
entry. Each `mov` places its constant in the return register. There is
one `ret` after all statements, so the runtime receives 3. Compound
expressions still use balanced pushes and pops to preserve intermediate
values. Linux exposes only the low eight bits of a normal exit status;
`1; -7;` therefore gives 249.

GCC assembles and links our emitted code with the C runtime. `-static`
follows upstream tests and `-Wl,-z,noexecstack` marks the stack
non-executable. Python does not use `eval()` or wrap the C compiler.

## Edge cases and existing differences

An empty or whitespace-only program is now accepted: it has zero statements.
Like the original, it emits only the function label and `ret`, without
setting `%rax`. Its exit status is not defined by this compiler, so tests
check its assembly rather than expecting an executable result.

A lone `;` or `1;;` is rejected. The current expression-statement rule
requires an expression; empty statements are not yet part of this grammar.
A semicolon inside parentheses, such as `(1; 2);`, is also rejected because
parentheses still contain an expression, not a statement list.

The earlier intentional Python/C differences remain: token lists and
dataclasses, explicit numeric-token bounds of 0 through 2147483647,
Unicode whitespace support, character positions instead of C byte offsets,
and buffered assembly output. Negative signs are separate tokens, so
`-2147483648;` still exceeds our literal policy. Arithmetic intermediates
use 64-bit registers. Deep expression trees can reach Python's recursion
limit, and division by zero remains unchecked at runtime.

## Tests and attribution

```sh
python3 python/test.py
```

All previous valid expression cases now end with `;`. Tests include all
27 original assertions through this commit, plus multiple compound
statements, last-result behavior, exact assembly order, statement-list
structure, empty-program assembly, and caret diagnostics for missing or
extra semicolons. Build artifacts use automatically cleaned temporary
folders.

All implementation changes are under `python/` on the `python-lessons`
branch. Original C files are intact. Original chibicc: Copyright (c) 2019
Rui Ueyama, MIT licensed. The full notice remains in `LICENSE` here and in
the repository root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
