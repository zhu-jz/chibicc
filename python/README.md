# Lesson 281: Support GNU case ranges

Original chibicc commit: [`d90c73b6058af4b22a4edd610713f75b2478e356`](https://github.com/rui314/chibicc/commit/d90c73b6058af4b22a4edd610713f75b2478e356).
Earlier explanations are available in Git history.

A case label can now specify an inclusive range: case 6 ... 20. The parser stores
both endpoints and rejects an inverted range. A one-value case keeps the existing
comparison. A range subtracts its lower bound from a copy of the switch value,
then uses an unsigned comparison against the range width.

```sh
printf 'int main(void){switch(7){case 0 ... 5:return 1;case 6 ... 20:return 42;}return 0;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly computes 7-6 and checks whether the unsigned result is at most 14 using
jbe. A value below 6 wraps to a large unsigned number and fails the comparison.
Tests cover both endpoints, values outside the range, negative bounds, a single
value, 64-bit switches and the empty-range diagnostic, plus original control.c.
Python stores case nodes in a list where C links them; both check newest cases
first and convert the endpoints through a signed 32-bit int in this commit.

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
