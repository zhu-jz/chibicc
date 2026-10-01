# Lesson 187: Add #error

Original chibicc commit: [`e7fdc2e3f1d20d38ad61f6cb87e72c613b7696c7`](https://github.com/rui314/chibicc/commit/e7fdc2e3f1d20d38ad61f6cb87e72c613b7696c7).
Earlier explanations are available in Git history.

An active `#error` directive immediately raises a compile error at the directive
name. It runs during preprocessing, including in `-E` mode. A directive inside
a skipped conditional branch is never visited and therefore does not fail.

The original implementation reports the literal message `error`; it does not
use any text after the directive. Python preserves that early behavior with
the existing CompileError type and source-location formatter. Included headers
retain their own filenames and line numbers in this diagnostic.

```sh
printf '#if 0\n#error unreachable\n#endif\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The inactive directive emits nothing; the selected main loads 42 into `%rax`
and returns. An active `#error` stops before assembly is written. Tests check
active and skipped branches, empty directive text, preprocessing-only mode,
empty assembly output on failure and diagnostics from included headers.

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
