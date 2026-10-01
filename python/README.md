# Lesson 203: Define functions returning aggregates

Original chibicc commit: [`d7bad961146b9f2fd918f05fd59a50f3f65bf325`](https://github.com/rui314/chibicc/commit/d7bad961146b9f2fd918f05fd59a50f3f65bf325).
Earlier explanations are available in Git history.

Return statements now preserve aggregate addresses instead of casting them.
For small results the compiler packs bytes into rax/rdx and loads floating
chunks into xmm0/xmm1. For large results the definition gains an anonymous
first pointer parameter, and the return statement copies bytes to that buffer.
Python keeps this hidden parameter in the ordinary parameter list.

```sh
printf 'struct T{int a;double b;};struct T f(void){return (struct T){12,30};}int main(void){return f().a+f().b;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The function packs the integer into rax and loads the double into xmm0. Main
copies those return registers into a local result buffer and reads its members.
Tests cover both mixed orders, floating chunks, tiny and large structs, unions,
GCC callers, hidden-parameter pressure and the original aggregate fixtures.
We preserve the original's eight-byte load for a floating second chunk, and
its large-return rax still points to the source rather than the destination;
these historical ABI limitations await their original fixes.

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
