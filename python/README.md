# Lesson 302: Link shared libraries with -shared

Original chibicc commit: [`4e5de36a36452ef9fe29ac55f7812f2bb9005d95`](https://github.com/rui314/chibicc/commit/4e5de36a36452ef9fe29ac55f7812f2bb9005d95).
Earlier explanations are available in Git history.

-shared asks ld to produce a shared library. The driver omits crt1.o, which normally
supplies the executable entry point, and selects crtbeginS.o/crtendS.o around the
inputs. -fPIC remains a separate option: -shared chooses the link form rather than
automatically changing generated addresses.

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson-library.c
printf 'int answer(void);int main(void){return answer();}\n' > /tmp/lesson.c
python3 python/main.py -fPIC -shared -o /tmp/lesson-library.so /tmp/lesson-library.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s /tmp/lesson-library.so
/tmp/lesson
echo $?  # 42
```

The caller's assembly obtains answer's address and calls it. The shared library
supplies its function returning 42. Tests build the library and executable using
the Python driver, run them, check shared startup objects and inspect ELF segments.
Python passes a shared-link boolean instead of using C's global option. The original
still supplies a dynamic-loader argument when not static; ld produces a shared
object without an INTERP segment despite that argument.

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
