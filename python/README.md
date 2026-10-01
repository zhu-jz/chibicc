# Lesson 264: Provide offsetof in stddef.h

Original chibicc commit: [`1b99badce48083c5fa6b8b5872e899c7d1a47f9a`](https://github.com/rui314/chibicc/commit/1b99badce48083c5fa6b8b5872e899c7d1a47f9a).
Earlier explanations are available in Git history.

The bundled stddef.h now defines offsetof(type,member) using a cast of zero to
an aggregate pointer, a member reference and its address, cast to size_t. Existing
layout and address-expression code already provide the implementation. There
is no new builtin or parser rule in this original commit.

```sh
printf '#include <stddef.h>\ntypedef struct{int a;char b;int c;double d;}T;int main(void){return offsetof(T,d)+26;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Layout aligns d to offset 16. Assembly computes its address from a zero base
without loading memory at that address, then adds 26 and returns 42. Tests cover
all four offsets, nested fields and array members, constant-expression use,
size_t width and the original offsetof.c fixture.
The header is copied byte-for-byte from this original revision. Python's member
objects carry offsets where C uses Member pointers; the macro's C spelling and
meaning are otherwise unchanged.
Python's separate constant evaluator now also handles numeric address constants,
which the original shared eval2 routine already supported. This lets offsetof
work in enum values as well as runtime expressions, without accepting unresolved
global symbol addresses as integer constants.

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
