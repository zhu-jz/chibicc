# Lesson 276: Pass library arguments to the linker

Original chibicc commit: [`bc2527944a83c1bc951a429530f39e93dc5235b2`](https://github.com/rui314/chibicc/commit/bc2527944a83c1bc951a429530f39e93dc5235b2).
Earlier explanations are available in Git history.

Arguments beginning with -l are now collected alongside input files and passed
to ld in their original order. They are not treated as source filenames. For
example, -lm asks the linker to resolve math functions from libm.

```sh
printf 'double sqrt(double);int main(void){return sqrt(1764.0);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s -lm
/tmp/lesson
echo $?  # 42
python3 python/main.py -o /tmp/lesson /tmp/lesson.c -lm
```

Assembly passes 1764 in xmm0, calls sqrt, and converts its floating return value
42 to the integer return register. GCC in the example and our compiler's driver
both link libm. A test links and runs that call through our own driver and checks
its traced linker arguments. Python uses the existing subprocess argument list;
the original accepts attached -lname syntax, without adding a separate -l name form.

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
