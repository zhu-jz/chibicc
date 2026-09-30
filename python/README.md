# Lesson 30: sizeof expressions

Original chibicc commit: [`3e55cafef80f0fc9d74bb06ea174de4b53e2ef94`](https://github.com/rui314/chibicc/commit/3e55cafef80f0fc9d74bb06ea174de4b53e2ef94).
Earlier explanations are available in Git history.

## What changed

`sizeof` reads a unary expression, annotates its type, and returns a numeric
node containing its size. No runtime node for the operand remains. Thus
`sizeof(x=2)` does not assign 2 to x, and `sizeof missing()` does not call or
require a definition of missing. The operand must still parse and type-check.

Parentheses can group a larger expression: `sizeof x+1` means `(sizeof x)+1`,
while `sizeof(x+1)` measures the whole addition. Type-name operands such as
`sizeof(int)` are not supported in this lesson. Arrays retain their full type
for sizeof, rather than converting to pointers: a 3-by-4 int array is 96 bytes,
one row is 32, and one element is 8 at this stage.

## Run it

```sh
python3 python/main.py 'int main(){int x[3][4]; return sizeof(*x);}' > /tmp/lesson30.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson30 /tmp/lesson30.s
/tmp/lesson30
echo $?
```

The executable prints nothing; the last command shows **32**. Use an interactive
shell without `set -e` for nonzero statuses. The body simply emits `mov $32,%rax`
and jumps to the main return label; no row is loaded.

Tests cover all twelve upstream examples, sizes for scalars/pointers/arrays,
precedence, suppressed assignments and calls, invalid operand types, and
keyword boundaries. Integers still occupy eight bytes. No new intentional
Python/C difference is introduced; size arithmetic uses Python integers.

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
