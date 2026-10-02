# Lesson 301: Link static executables with -static

Original chibicc commit: [`1e9b6dd1108690f22c84af8db606fea9fb7ec2db`](https://github.com/rui314/chibicc/commit/1e9b6dd1108690f22c84af8db606fea9fb7ec2db).
Earlier explanations are available in Git history.

-static selects a statically linked executable. The driver forwards -static to ld,
omits the dynamic-loader argument and groups libgcc, libgcc_eh and libc so their
archive members can resolve mutual references. Ordinary dynamic links retain
their loader and shared support-library arguments.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -static -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
python3 python/main.py -static -o /tmp/lesson /tmp/lesson.c
```

Assembly is unchanged: main returns 42 in rax. Static linking copies needed runtime
code from archives into the executable instead of recording a dynamic interpreter.
Tests use the Python driver to build and run a static puts call, inspect the linker
trace and confirm that readelf reports no INTERP segment; dynamic-link tests remain.
Python builds explicit argument lists rather than C StringArray globals. As in
the original, startup object selection still uses crtbegin.o in this step.

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
