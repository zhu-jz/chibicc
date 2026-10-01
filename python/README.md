# Lesson 252: Skip pragma directives

Original chibicc commit: [`74ec9f6f3964d4beaa3970bd99c8660f958b694e`](https://github.com/rui314/chibicc/commit/74ec9f6f3964d4beaa3970bd99c8660f958b694e).
Earlier explanations are available in Git history.

Preprocessing now discards `#pragma` and the remainder of its physical line.
This permits sources containing implementation-specific directives to compile.
At this historical step every pragma is ignored, including `once` and `pack`.

```sh
printf '#pragma unknown example\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The pragma emits no tokens or assembly. Main loads 42 and returns normally.
Tests verify arbitrary, empty and end-of-file pragmas, unchanged struct alignment
under `pack`, and repeated inclusion despite `once`, plus the original fixtures.
Python stops at EOF as well as the next line; the C loop assumes it can advance
until a token begins a line. The EOF guard avoids an invalid pointer traversal
without adding semantics for any particular pragma.

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
