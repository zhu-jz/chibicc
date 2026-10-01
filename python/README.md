# Lesson 247: Read GNU preprocessor line markers

Original chibicc commit: [`aaf20fb96eaf21ead775fde6bad00d8e71650b5a`](https://github.com/rui314/chibicc/commit/aaf20fb96eaf21ead775fde6bad00d8e71650b5a).
Earlier explanations are available in Git history.

A numeric preprocessing token immediately after `#` now selects the line-marker
parser. This accepts the GNU output form without the `line` keyword, including
optional trailing flags. The same file state and token snapshots from the last
lesson handle the logical line and filename changes.

```sh
printf '# 41 "virtual.c" 2 3\nint main(void){return __LINE__;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The marker disappears during preprocessing and `__LINE__` becomes 42, which the
assembly loads into the return register. Tests exercise both filename forms,
invalid non-int marker numbers and the expanded original line.c fixture.
Trailing flags are consumed with the directive but have no effect in this
original implementation. The previous historical off-by-one rule remains.
Python dispatches on the token kind string instead of C's token-kind enum.

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
