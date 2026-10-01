# Lesson 234: Advertise UTF character encodings

Original chibicc commit: [`e4491b811510d08f880d0f9c7553ecfd18635469`](https://github.com/rui314/chibicc/commit/e4491b811510d08f880d0f9c7553ecfd18635469).
Earlier explanations are available in Git history.

Two predefined object-like macros, __STDC_UTF_16__ and __STDC_UTF_32__, now
expand to 1. They let source and headers select code for the u and U character
and string encodings introduced in the preceding lessons. Normal command-line
-D/-U and source #define/#undef behavior also applies to these names.

```sh
printf 'int main(void){return __STDC_UTF_16__+__STDC_UTF_32__+40;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Preprocessing replaces each macro with 1; the usual arithmetic instructions
return 42. Tests check values, defined/#if selection, -U removal and original
fixtures. Python adds two entries to the explicit predefined dictionary where
C calls define_macro twice. This commit advertises the historical encoding
support; it changes no parser, payload or assembly-generation algorithm.

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
