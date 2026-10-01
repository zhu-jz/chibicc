# Lesson 182: Preserve macro expansion spacing

Original chibicc commit: [`8075582c21496530e3b1847f5bad11c42941066e`](https://github.com/rui314/chibicc/commit/8075582c21496530e3b1847f5bad11c42941066e).
Earlier explanations are available in Git history.

The first replacement token now inherits the invoking macro token's beginning-
of-line and preceding-space flags. Empty replacements transfer those flags to
the following token. A substituted argument's first token similarly inherits
the parameter's flags from the replacement body.

These flags do not change expression evaluation, but they affect `-E` output
and stringizing through another macro. A wrapper containing `foo.x` now yields
`"foo.bar"`, while `foo. x` yields `"foo. bar"`. The change uses straightforward
field assignments, matching the original C metadata updates.

```sh
printf '#define VALUE 42\nint main(void){return VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly still loads 42 into `%rax` and returns. New tests inspect nested
stringizing with and without spaces, retained newlines for both macro kinds,
spacing after empty expansion and executable behavior. The earlier recursive
macro output snapshot changes to reflect the corrected leading-space behavior.

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
