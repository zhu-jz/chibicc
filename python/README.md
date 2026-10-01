# Lesson 282: Support GNU array range designators

Original chibicc commit: [`3d5550e29a92708613c3a351c0857aea90e147a5`](https://github.com/rui314/chibicc/commit/3d5550e29a92708613c3a351c0857aea90e147a5).
Earlier explanations are available in Git history.

An initializer can now select an inclusive array range with [2 ... 4]=7. The parser
reads both bounds, applies the following initializer to each selected child and
continues after the range. The existing inferred-bound scan already recognizes
the final range endpoint, so unsized arrays receive sufficient storage.

```sh
printf 'int main(void){int x[]={[2 ... 4]=7,21};return x[2]+x[3]+x[4]+x[5];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly zeroes the local array, writes 7 into elements 2 through 4 and 21 into
element 5, then adds them. Tests cover inferred bounds, overwrites, global arrays,
member designators, range errors and the original initializer fixture.
This original implementation reparses the value for each element, so a local
side effect such as ++i runs once per selected element; GNU's usual single-evaluation
rule is not implemented yet. Nested designation resumes at begin+1 as in C.
Python retains its explicit negative-index rejection instead of indexing before
C's children array; its diagnostics point at the opening bracket.

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
