# Lesson 217: Check build warnings and non-returning helpers

Original chibicc commit: [`2c91da54dff93a365feec5a34f8eaeccca3e3a70`](https://github.com/rui314/chibicc/commit/2c91da54dff93a365feec5a34f8eaeccca3e3a70).
Earlier explanations are available in Git history.

The original enables GCC warnings for the compiler's own build and marks its
fatal error helpers noreturn. Python has no C compiler-warning pass, so the
corresponding build target checks every Python module with py_compile and
warnings treated as errors. make all and make test-all include this check.
The always-exiting usage helper is annotated with typing.NoReturn.

```sh
make -C python check all
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/build/chibicc.pyz -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

This build-quality lesson does not change generated instructions; main still
places 42 in rax and returns. Validation checks syntax/warnings, archive build,
the packaged multi-file pipeline and original C fixtures. Python's check is
an explicit adaptation, not a substitute claim that GCC's -Wall analysis runs
on Python or that py_compile is a static type checker. Compiler errors already
raise exceptions, preserving the original non-returning control flow.

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
