# Lesson 13: blocks with braces

This educational Python port implements original chibicc commit
[`18ac283a5d19c19f1e1a7020a50fe34c2160a0f8`](https://github.com/rui314/chibicc/commit/18ac283a5d19c19f1e1a7020a50fe34c2160a0f8),
“Add { ... }.” Earlier lessons remain in Git history; lesson 12 is Python
commit `645f8e6`.

## What changed

The entire program must now be enclosed in `{` and `}`. Inside it, a block
can appear wherever a statement can appear:

```text
{ return 42; }
{ {1; {2;} return 3;} }
{ a=1; {a=4; b=3;} return a+b; }
```

These programs return 42, 3, and 7 respectively. Expression and return
statements still require semicolons. A block needs no semicolon after its
closing brace. Empty blocks `{}` are accepted; a lone `;` is still not a
statement in this grammar.

Blocks only group statements in this lesson. They do not introduce local
variable scope or allocate a separate stack frame. The third example can
read `b` after its inner block, and assignment to `a` updates the same
variable object used outside. A `return` in any nested block exits the
whole function, not just that block.

## Parser and tree

The new grammar rules are:

```text
program       = "{" compound-stmt
stmt          = "return" expr ";" | "{" compound-stmt | expr-stmt
compound-stmt = stmt* "}"
```

The opening brace has already been consumed when `compound_stmt()` starts.
It repeatedly calls `stmt()` until it finds the closing brace. Since
`stmt()` can call `compound_stmt()` again, this supports nested blocks.

`common.py` adds a `body` list to `Node`. A node with `kind="BLOCK"` holds
its child statements there. `Function.body` now refers to the outer block
node rather than directly to a list. For `{ {1;} return 2; }`:

```text
BLOCK
├── BLOCK
│   └── EXPR_STMT(NUM(1))
└── RETURN(NUM(2))
```

The original stores each block's children as a linked list. Python uses a
list with `default_factory=list`, giving each block its own child list.
This avoids accidentally sharing a mutable default between nodes.

## Assembly generation

`gen_stmt()` recognizes a block and recursively generates its children in
order. Braces need no machine instruction: `{ {1;} return 2; }` produces
the same body instructions as a flat sequence of those statements:

```asm
  mov $1, %rax
  mov $2, %rax
  jmp .L.return
```

The first `mov` sets 1, the second sets 2, and the jump reaches the shared
function epilogue. Nested blocks use the same local-variable offsets and
the same `.L.return` label. Temporary expression pushes and pops must still
balance; the original commit checks depth after generating the outer block,
which this port also does.

## Run it in WSL

With Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py '{ {1; {2;} return 3;} }' > /tmp/chibicc-python-lesson13.s
cat /tmp/chibicc-python-lesson13.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson13 /tmp/chibicc-python-lesson13.s
/tmp/chibicc-python-lesson13
echo $?
```

The last command prints **3**. Quote the input so the shell passes braces,
semicolons, and operators literally. The executable prints nothing itself;
`echo $?` immediately afterward displays its exit status. Use an ordinary
interactive shell: `set -e` would stop a script on status 3.

The generated function still has a prologue that saves `%rbp` and reserves
aligned local storage, followed by the statements and a shared epilogue:

```asm
.L.return:
  mov %rbp, %rsp
  pop %rbp
  ret
```

The epilogue restores the caller's stack while preserving the result in
`%rax`. GCC assembles and links our output with the C runtime. `-static`
follows the original tests and `-Wl,-z,noexecstack` marks the stack
non-executable. Python does not use `eval()` or invoke the original C compiler.

## Exact behavior of this original commit

Bare input such as `return 1;` now reports `expected '{'`. Empty input is
also rejected, while an empty outer block is valid but sets no result.
Missing closing braces reach EOF while trying to parse a statement and
report `expected an expression`; this follows the original diagnostic.

The original parser does not check for leftover tokens after the outer
closing brace. This port preserves that quirk: `{return 3;} return 9;`
compiles just the first block. The tokenizer still scans all input, so an
invalid character in the ignored suffix can still produce an error. This
behavior is documented and tested rather than silently changing the lesson.

The earlier Python/C differences remain: lists and dataclasses instead of
linked structs, parser state per instance, explicit numeric-token bounds
of 0 through 2147483647, Unicode whitespace, character-based diagnostic
positions, and assembly buffered until compilation succeeds. Variables
remain uninitialized until assigned, arithmetic uses 64-bit registers,
and normal exit statuses retain eight bits. Deep nesting can reach Python's
recursion limit; runtime division by zero remains unchecked.

## Tests and attribution

```sh
python3 python/test.py
```

Earlier source fixtures are wrapped in the required outer braces. Tests
retain all earlier executable cases and cover the original nested-block
example, nested tree structure, exact assembly, empty blocks, shared
variables across blocks, return from a nested block, missing braces, and
the upstream trailing-token behavior. Temporary build artifacts are cleaned
up automatically.

All implementation changes are in `python/` on `python-lessons`; original
C files remain intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The complete notice remains in `LICENSE` here and in the repository
root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
