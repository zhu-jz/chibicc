# Lesson 242: Select struct fields in initializers

Original chibicc commit: [`67f5834378660abf271722a16294a634106d047e`](https://github.com/rui314/chibicc/commit/67f5834378660abf271722a16294a634106d047e).
Earlier explanations are available in Git history.

Struct initializers now accept .field designators, including nested chains
such as .part.value and combinations such as [1].value or .items[2]. Values
after a selected field continue through the enclosing initializer. A field
write into an earlier whole-struct copy clears that copy expression so the
explicit field initializer and zero-filled remaining fields take effect.

```sh
printf 'int main(void){struct T{int a,b,c;}x={.c=30,.a=12};return x.a+x.b+x.c;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The initializer tree assigns a=12 and c=30; local zeroing leaves b=0. Ordinary
member stores and loads produce the assembly and return 42. Tests cover globals,
nested fields and arrays, inferred arrays of structs, replacement of a prior
copy, bitfields, optional equals syntax, diagnostics and original fixtures.
Python uses member indices to resume its list rather than C next pointers,
and reports missing names safely instead of dereferencing unnamed members.
This commit supports named struct fields only: union field designators and
anonymous-member designator lookup are not added ahead of their original steps.
The original brace-free continuation parser's comma behavior is retained.

This finishes lessons 193–242, fifty consecutive original commits. This README
explains the current lesson; earlier explanations remain in Git history.
For full source and packaged-compiler verification, run make -C python test-all.

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
