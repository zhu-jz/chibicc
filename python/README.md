# Lesson 164: Skip nested conditionals in false branches

Original chibicc commit: [`aa570f3086ce3e2c5ac8bf6107c051fed5aabf89`](https://github.com/rui314/chibicc/commit/aa570f3086ce3e2c5ac8bf6107c051fed5aabf89).
Earlier explanations are available in Git history.

Skipping a false `#if` now recognizes nested `#if` blocks and recursively skips
them through their matching `#endif`. Expressions and includes inside skipped
blocks are never processed. The recursion follows the original implementation.
Python returns safely at end of input so an incomplete nested block reports an
unterminated directive instead of following a null C token pointer.

```sh
printf '#if 0\n#if unknown\ninvalid C\n#endif\n#endif\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Only the `main` function reaches the parser. Its assembly loads the return
value into `%rax`, restores the stack frame and returns. Tests exercise nested
skips, ignored expressions and missing includes, executable exit status, and
an incomplete nested directive. The original macro fixture also runs directly
through the Python preprocessor.

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
