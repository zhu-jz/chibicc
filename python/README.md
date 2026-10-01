# Lesson 103: Struct copy initializers

Original chibicc commit: [`aca19dd35027a12e245bfa52e6a98968e0cd2a9c`](https://github.com/rui314/chibicc/commit/aca19dd35027a12e245bfa52e6a98968e0cd2a9c).
Earlier explanations are available in Git history.

## What changed

A struct initializer may now be a struct expression again: `struct T y=x;`.
The parser first tries an assignment expression when there is no opening brace.
If its type is STRUCT, it stores that expression in the initializer rather than
populating member children. Lowering creates one whole-object assignment;
brace lists still create individual member assignments.

This repairs the temporary restriction introduced in lesson 102. The emitter
already knows how to copy aggregate bytes, so it needs no changes. Python uses
an optional expression field instead of a nullable C node pointer. As upstream,
this step checks STRUCT kind rather than implementing full type compatibility.

## Assembly and WSL example

```sh
printf 'int main(){struct T{int a,b;} x={1,42};struct T y=x;return y.b;}\n' > /tmp/lesson103.c
python3 python/main.py /tmp/lesson103.c > /tmp/lesson103.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson103 /tmp/lesson103.s
/tmp/lesson103
echo $?
```

The emitter clears y, computes both addresses, then copies its eight bytes
using r8b. Loading y.b produces exit status 42. Tests cover parentheses, nested
member copies, larger objects, emitted byte copying, and upstream examples.

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
