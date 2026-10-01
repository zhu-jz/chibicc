# Lesson 189: Add __FILE__ and __LINE__

Original chibicc commit: [`6f17071885b98ac5dcdcc0b233ff204150a6826c`](https://github.com/rui314/chibicc/commit/6f17071885b98ac5dcdcc0b233ff204150a6826c).
Earlier explanations are available in Git history.

Two dynamic predefined macros now create tokens from the source location.
`__FILE__` becomes a quoted filename and `__LINE__` becomes an integer. Unlike
fixed replacement bodies, their handlers inspect each invocation separately.

Every ordinary macro replacement token records the invoking token as its
origin. Dynamic handlers follow that chain to the original call location, so
`#define LINE() __LINE__` reports where LINE is used, including when defined
in a header and invoked in its caller. Python uses callable fields and token
references in place of C function pointers and linked origin pointers. Raw
in-memory tokenizer tests use '-' when no filename exists.

```sh
printf '#define LINE() __LINE__\n\nint main(void){return LINE();}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 3
```

Expansion supplies the number 3; assembly loads it into `%rax` and returns.
Tests check direct and chained expansions, header versus caller filenames and
line numbers, and executable results. Upstream fixtures run from the Python
directory with paths such as test/macro.c, matching their filename assertions.

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
