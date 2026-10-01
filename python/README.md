# Lesson 166: Add #elif

Original chibicc commit: [`e7a1857a31fc0c0012773c021639a6297f5b208f`](https://github.com/rui314/chibicc/commit/e7a1857a31fc0c0012773c021639a6297f5b208f).
Earlier explanations are available in Git history.

`#elif` extends an open conditional with another constant expression. It is
evaluated only when no earlier branch was included. The first successful
branch wins; subsequent expressions and bodies are skipped, including invalid
expressions in those discarded branches. `#elif` after `#else` is an error.

The conditional stack now distinguishes its first branch, an `#elif` branch,
and `#else`. Skipping stops at a sibling `#elif`, `#else`, or `#endif`, while
nested conditionals are passed completely. Python uses explicit assignments
and branching in place of the C output-pointer expression.

```sh
printf '#if 0\n#elif 2+3\nint main(void){return 42;}\n#else\ninvalid\n#endif\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The selected `main` loads 42 into `%rax` and returns through the usual frame
cleanup. Selection happens before parsing, so discarded code emits no assembly.
Tests cover a chain of alternatives, skipped expressions, fallback branches,
diagnostics, and the unchanged original macro fixture.

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
