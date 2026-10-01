# Lesson 223: Normalize source newlines before tokenizing

Original chibicc commit: [`74bcec5b22a601451fac9d0878003d04205abca6`](https://github.com/rui314/chibicc/commit/74bcec5b22a601451fac9d0878003d04205abca6).
Earlier explanations are available in Git history.

File and stdin input now convert CRLF and lone CR to LF before removing
backslash-newline pairs. This gives Windows, old-Mac and Unix line endings
the same preprocessing and diagnostic behavior. It also lets a backslash at
the end of a CRLF line continue a macro definition correctly.

```sh
printf '#define VALUE \\\r\n42\r\nint main(void){return VALUE;}\r\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The source becomes the usual VALUE macro definition and main loads 42 into
rax. Tests cover all three newline forms, continuation, normalized File text,
preserved line numbers, diagnostics and original fixtures. Python creates
normalized strings with ordered replacements; C compacts its character buffer
in place. Raw tokenize still consumes the supplied string directly, while
all real compiler file/stdin input uses the new normalization pipeline.

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
