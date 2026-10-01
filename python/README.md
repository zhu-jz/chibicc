# Lesson 197: Build through the complete preprocessing pipeline

Original chibicc commit: [`12a9e7506c092fcbab8852db85c3aebefc8a8c81`](https://github.com/rui314/chibicc/commit/12a9e7506c092fcbab8852db85c3aebefc8a8c81).
Earlier explanations are available in Git history.

The original C build now compiles its compiler sources directly with chibicc,
including its own preprocessor, and deletes the source-rewriting self.py script.
Its ordinary tests also explicitly search the bundled include directory.
There is no compiler algorithm change in this commit.

The Python port never needed a C source-rewriting bootstrap script. Python
executes its implementation, while the implementation compiles C into native
assembly. Its build milestone is a packaged compiler with sibling headers and
the same complete C preprocessing/parsing/generation pipeline. This is an
intentional build adaptation, not a claim that this C compiler compiles its own
Python source or that packaging is native self-hosting. The original C files
remain intact. Both upstream test runs explicitly use their bundled headers.

```sh
python3 python/build.py
printf '#include <stdbool.h>\nint main(void){bool ready=true;return ready+41;}\n' > /tmp/lesson.c
python3 python/build/chibicc.pyz -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The archive expands the header, stores a boolean byte, adds 41 to its loaded
value and returns 42 in %rax. A new integration test builds the archive outside
the repository, compiles and links two C inputs using stdbool.h and stdarg.h,
and runs the result. It also checks emitted call assembly. The complete source
and packaged suites are run for this build milestone.

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
