# Lesson 214: Reject addresses of bitfields

Original chibicc commit: [`c302a969d8217ab46113d494b8cd773cf057193d`](https://github.com/rui314/chibicc/commit/c302a969d8217ab46113d494b8cd773cf057193d).
Earlier explanations are available in Git history.

Unary & now checks the typed operand and reports cannot take address of
bitfield for a direct bitfield member. A field can start between bytes and
share storage with neighbors, so C has no ordinary pointer to its value.
Taking the containing struct's address remains valid, including the temporary
used by compound assignments. Python raises CompileError at the & token.

```sh
printf 'int main(void){struct T{int a:3;int b;}x={1,42};int*p=&x.b;return *p;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The ordinary member b still has a byte address: lea plus its offset forms
the pointer, and the load returns 42. Replacing &x.b with &x.a gives the new
diagnostic before assembly generation. Tests cover direct, parenthesized and
arrow forms, valid ordinary members, existing bitfield updates and upstream
fixtures. There is no new runtime instruction for this parser restriction.

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
