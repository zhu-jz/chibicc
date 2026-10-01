# Lesson 243: Choose a union member in an initializer

Original chibicc commit: [`31dc1dfa211ee27e74907ce3aa3986401dcedb82`](https://github.com/rui314/chibicc/commit/31dc1dfa211ee27e74907ce3aa3986401dcedb82).
Earlier explanations are available in Git history.

A union stores all its members at the same address. Initializers now record
which member was selected by a `.field` designator instead of always writing
the first member. Nested array and struct designators can select a union member
too. Without a designator, the first member is still the default.

```sh
printf 'int main(void){union T{int a;char b[4];}x={.b[1]=42};return x.b[1];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Local assembly zeroes the union, then stores one byte at its base address plus
one. Loading that byte and returning it gives exit status 42. Global initializers
write the selected member into the shared byte buffer instead. Tests also cover
empty global arrays of unions and nested selections, alongside original fixtures.
Python stores the selected Member object or None instead of a nullable C pointer.
The original restriction to a single initializer inside a union is preserved;
a trailing comma in the designated form is not accepted at this step.

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
