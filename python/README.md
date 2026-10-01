# Lesson 169: Expand macros in conditional expressions

Original chibicc commit: [`2651448084a56dd0b960989798772e71e12e6c30`](https://github.com/rui314/chibicc/commit/2651448084a56dd0b960989798772e71e12e6c30).
Earlier explanations are available in Git history.

Before evaluating a `#if` or eligible `#elif` expression, the preprocessor now
expands macros in its copied token line. The same macro definitions are shared
with ordinary source processing. Keyword conversion and the final unmatched
conditional check remain in the outer entry point.

A small internal preprocessing function accepts the shared dictionaries and
conditional stack explicitly instead of relying on C global variables. Empty
expansions produce `no expression`; identifiers that remain undefined still
produce the parser's undefined-variable diagnostic at this historical step.

```sh
printf '#define VALUE 5\n#if VALUE-5\ninvalid\n#elif VALUE\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The first expression becomes `5-5`, selecting the second branch. Generated
assembly loads 42 into `%rax` and returns; macro evaluation adds no runtime
instructions. Tests cover chained definitions, arithmetic conditions, empty
expansions and expressions skipped after an earlier successful branch.

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
