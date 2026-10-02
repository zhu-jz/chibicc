# Lesson 300: Continue include searches with include_next

Original chibicc commit: [`f10bcebaa5df6bcb8e08e622ac44b0098e3133ae`](https://github.com/rui314/chibicc/commit/f10bcebaa5df6bcb8e08e622ac44b0098e3133ae).
Earlier explanations are available in Git history.

GNU #include_next searches later include directories rather than starting from the
first one. A successful ordinary path search records the index after its matched
directory. include_next uses that shared cursor and ignores quote-versus-angle
local-directory handling, allowing a wrapper header to reach another header.

```sh
mkdir -p /tmp/lesson-next1 /tmp/lesson-next2
printf '#include_next <answer.h>\n' > /tmp/lesson-next1/answer.h
printf '#define ANSWER 42\n' > /tmp/lesson-next2/answer.h
printf '#include <answer.h>\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -I/tmp/lesson-next1 -I/tmp/lesson-next2 -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The first header reaches the second one, which defines ANSWER; assembly returns
its expanded value 42. Tests follow the original three-directory wrapper chain.
The cursor is shared, not a per-header origin. Cache hits do not update it, and a
successful include_next search does not advance past its matched directory; these
historical details are preserved. Python uses a module integer instead of a C
static integer. A failed search falls back to the supplied filename as before.

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
