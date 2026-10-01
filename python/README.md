# Lesson 113: Initializing flexible array members

Original chibicc commit: [`cd688a89b8a57e9614f278e29a9267709494d236`](https://github.com/rui314/chibicc/commit/cd688a89b8a57e9614f278e29a9267709494d236).
Earlier explanations are available in Git history.

## What changed

Types now remember that their final member was a flexible array. When a whole
object is initialized, that member's initializer can infer an element count.
The parser copies the object's type and member records, completes the last member,
and adds its storage size. Other objects and the shared struct tag retain their
original zero-length tail.

Python dataclasses.replace copies member records; the completed type is returned
through the initializer rather than a C Type output pointer. This matches the
original size rule: append the tail size without introducing a new layout or
alignment policy. Flexible-tail initialization is an extension to standard C.
Only top-level object initialization enables the flexible child at this step.

## Assembly and WSL example

```sh
printf 'int main(){struct T{int a;int b[];} x={1,2,42};return x.b[1];}\n' > /tmp/lesson113.c
python3 python/main.py /tmp/lesson113.c > /tmp/lesson113.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson113 /tmp/lesson113.s
/tmp/lesson113
echo $?
```

This object's completed size is 12 bytes. Assembly clears that storage and writes
its fixed int plus two tail ints. The final value returns 42. Tests check locals,
global byte data, string tails, independent completed object sizes, unchanged
shared tags, member-record copying, actual executables, and upstream examples.

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
