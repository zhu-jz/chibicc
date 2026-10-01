# Lesson 273: Add pointer arithmetic for variable-length arrays

Original chibicc commit: [`07f901057f5c6aa77c0f15f7a22dc0b88923c227`](https://github.com/rui314/chibicc/commit/07f901057f5c6aa77c0f15f7a22dc0b88923c227).
Earlier explanations are available in Git history.

A VLA variable stores its allocated address in an eight-byte local slot. Reading
its address now loads that slot; a separate VLA_PTR node addresses the slot when
initializing it. Array expressions remain addresses rather than loading an element.
When an element is itself a VLA, pointer addition and subtraction multiply the
index by its saved runtime byte size. This makes multidimensional indexing work.

```sh
printf 'int main(void){int n=3,m=5;int x[n][m];x[2][4]=42;return x[2][4];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly loads the allocated base address, multiplies row 2 by the saved 20-byte
row size, and adds column 4 times four bytes. It writes 42 there and loads it back
for the return value. Tests cover one and two dimensions, reversed addition and
subtracting a row from a pointer, as well as the original VLA fixture.
Python uses a string node kind instead of C's enum. The original VLA subtraction
branch does not distinguish a numeric right operand from another pointer; this
lesson does not extend pointer-difference semantics beyond that implementation.

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
