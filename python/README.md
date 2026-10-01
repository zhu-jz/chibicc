# Lesson 167: Add object-like macros

Original chibicc commit: [`97d33ad3bdc21c26356253046902d4b166bd115b`](https://github.com/rui314/chibicc/commit/97d33ad3bdc21c26356253046902d4b166bd115b).
Earlier explanations are available in Git history.

`#define NAME replacement` stores a line of replacement tokens. Encountering
that identifier copies its body into the token stream and resumes scanning,
so replacements can contain other macro names. A dictionary records the most
recent definition, replacing the original C linked-list search. Definitions
share state across included files but are reset for each compilation.

Expansion is token substitution: strings are untouched, empty bodies remove
the name, and operator precedence is determined after substitution. Conversion
of identifiers to keywords still happens last, allowing a keyword spelling to
be a macro name. This historical step has no protection against recursive
macro definitions, and does not expand macros in `#if` expressions yet.

```sh
printf '#define VALUE 3+4\nint main(void){return VALUE*5;}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 23
```

After expansion the parser sees `3+4*5`. Assembly multiplies 4 by 5, adds 3,
leaves 23 in `%rax`, and returns. Tests cover precedence, replacement, chained
and empty macros, strings, keyword spellings, discarded definitions and errors.

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
