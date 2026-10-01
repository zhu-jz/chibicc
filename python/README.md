# Lesson 184: Add angle-bracket and macro-expanded includes

Original chibicc commit: [`d85fc4ffcfb8875aa191481e5c153a1e07066f8e`](https://github.com/rui314/chibicc/commit/d85fc4ffcfb8875aa191481e5c153a1e07066f8e).
Earlier explanations are available in Git history.

Include operands now accept quoted strings, tokens between angle brackets,
or an identifier whose expanded line becomes one of those forms. Quoted
filenames use their original text instead of decoded string bytes, preserving
literal backslashes. Angle-bracket filenames are reconstructed from tokens.

Both forms first try a relative path beside the including file. If that path
is absent, the filename itself is opened, allowing a working-directory path.
This historical step has no configurable or system include search directories
yet. The quote/angle distinction is recorded for the next stages. Python uses
its existing filesystem operations and explicit return values instead of C
output pointers. An unmatched angle bracket produces a diagnostic.

```sh
printf '#define VALUE 42\n' > /tmp/answer.h
printf '#define HEADER <answer.h>\n#include HEADER\nint main(void){return VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

After including and expanding VALUE, assembly loads 42 into `%rax` and returns.
Tests cover direct angle brackets, macro-expanded quoted or partial angle
forms, raw backslashes, working-directory fallback and missing closing brackets.
The updated original macro program includes both new headers unchanged.

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
