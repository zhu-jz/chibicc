# Lesson 239: Select array elements in initializers

Original chibicc commit: [`c618c3b582de1d0b10b334a4f2ba6b85d5128940`](https://github.com/rui314/chibicc/commit/c618c3b582de1d0b10b334a4f2ba6b85d5128940).
Earlier explanations are available in Git history.

An array initializer can now move its cursor with [index]=value. Subsequent
ordinary values continue after that element. Nested designators reach nested
arrays; the brace-free continuation logic stops before an outer designator so
its enclosing initializer can resume. Repeated writes replace the stored
initializer expression, while untouched elements retain zero or an earlier value.

```sh
printf 'int main(void){int x[6]={[4]=42};return x[4]+x[0];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The initializer tree stores 42 at element four. Local zeroing plus the ordinary
indexed assignment produces the assembly; globals use the same tree serializer.
Tests cover cursor movement, repeated writes, nested arrays, compound literals,
zero filling, bounds/type errors and original fixtures. Python returns the
index and next token as a tuple. It explicitly rejects negative indices instead
of allowing C's out-of-bounds pointer access or Python's wraparound indexing.
Inferred array bounds do not yet understand designators in this original step.

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
