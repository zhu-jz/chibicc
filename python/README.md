# Lesson 163: Add #if and #endif

Original chibicc commit: [`bf6ff928ad17d98d07f68f619e6cbe29829d0a20`](https://github.com/rui314/chibicc/commit/bf6ff928ad17d98d07f68f619e6cbe29829d0a20).
Earlier explanations are available in Git history.

`#if` evaluates a constant expression before parsing the program. A zero
result discards tokens through the next `#endif`; a nonzero result retains
them. A Python list records open directives and diagnoses unmatched endings.
The existing expression parser and constant evaluator perform the calculation.
No Python `eval()` is involved.

This original commit does not correctly skip nested conditionals in a false
branch: it stops at the first `#endif`. Tests preserve that historical behavior.
True nested branches work. Empty expressions, extra tokens, stray endings and
unterminated conditionals produce diagnostics. Python already handles a final
source line without a newline when displaying diagnostics, matching the C fix.

```sh
printf '#if 1\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The selected return expression loads 42 into `%rax` and jumps to the function
return label; the epilogue restores `%rbp` and returns. Preprocessor directives
produce no assembly. `-E` lets you inspect the selected tokens directly.

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
