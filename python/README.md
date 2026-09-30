# Lesson 39: GNU statement expressions

Original chibicc commit: [`9dae23461eb6250865f4ee727a0e727a6a4e03ba`](https://github.com/rui314/chibicc/commit/9dae23461eb6250865f4ee727a0e727a6a4e03ba).
Earlier explanations are available in Git history.

## What changed

A parenthesized block `({ statements; })` can now appear as an expression.
The parser creates STMT_EXPR with the block's statement list. Type annotation
requires its last statement to be an expression statement and uses that
expression's type. Empty blocks or a final declaration/return are rejected
because statement expressions returning void are not supported at this stage.

Code generation executes each statement using the existing statement generator.
The final expression leaves its result in `%rax`, ready for enclosing arithmetic,
assignment, calls, or dereference. A return inside the block still jumps to the
containing function's cleanup label; it does not return merely from the block.
Locals still use the existing function-wide name list, matching upstream's
current scope behavior.

## Run it

```sh
python3 python/main.py 'int main(){return ({int x=3; x=x+2; x;});}' > /tmp/lesson39.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson39 /tmp/lesson39.s
/tmp/lesson39
echo $?
```

The executable prints nothing; the last command shows **5**. Use an interactive
shell without `set -e` for nonzero statuses. The emitted assignments store into
x's stack slot; the final load places its value in `%rax` before main returns.
This syntax is a GNU C extension rather than standard C.

Tests cover all upstream examples, arithmetic combinations, a return escaping
the block, declarations, pointer-valued blocks, sizeof, and unsupported
valueless blocks. Python uses its list's final element where C walks to the
last linked-list node. No new intentional behavioral difference is introduced.

## Tests and attribution

Run from the repository root on x86-64 Linux/WSL with Python 3 and GCC
(`build-essential` on Ubuntu):

```sh
python3 python/test.py
```

The tests check emitted assembly and assemble/link/run real executables;
temporary artifacts are cleaned up and execution has a timeout.
Python builds syntax trees and emits assembly; it does not use `eval()`
or invoke the original compiler. Python lists, dataclasses, tuples, and
`None` replace C linked lists, structs, output pointers, and null pointers.
Unicode whitespace and character-based diagnostic positions are intentional
Python differences. Any further differences for this step are described above.

The implementation is in `python/` on `python-lessons`. Original C files
are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed.
The full notice is preserved in [LICENSE](LICENSE); this port uses the same license.
