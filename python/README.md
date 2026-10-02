# Lesson 311: Add the pinned CPython workflow

Original chibicc commit: [`2ed3fdafa3d2f60bd1bcdb2bc5df6c1e58c357f7`](https://github.com/rui314/chibicc/commit/2ed3fdafa3d2f60bd1bcdb2bc5df6c1e58c357f7).
Earlier explanations are available in Git history.

The original commit adds an optional CPython build-and-test script pinned to
`c75330605d4795850ec74fdc4d69aa5d92f76c00`. Its configure script mistakes
`chibicc` for Intel's `icc` because of substring matching, so it deletes lines
1996–2011 of `configure.ac`, runs `autoreconf`, and builds/tests with chibicc.

The Python runner now provides the same workflow. It uses an isolated checkout,
HTTPS instead of requiring GitHub SSH credentials, and a marker to avoid
repeating the configure edit on subsequent runs. The original shell fixture is
preserved byte for byte. Running the real optional workflow needs network access,
Autoconf and CPython's build dependencies; its full external test suite has not
been run as part of this lesson. Dry-run and patch tests validate its commands.

```sh
python3 python/thirdparty.py cpython --dry-run --jobs 2
cat >/tmp/lesson.c <<'C'
int main(void) { return 42; }
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Drop `--dry-run` to fetch the pin, build the Python compiler archive and attempt
the external workflow. Compiler syntax and assembly are unchanged: this example
still places the result in the accumulator and returns through `main`'s epilogue.
Tests check the exact line removal, repeat-run behavior, pin, command order,
and existing third-party workflows.

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
