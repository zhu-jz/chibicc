# Lesson 246: Track logical source lines and filenames

Original chibicc commit: [`c61c0d00252a8704ff2731f6a57bad3657b84170`](https://github.com/rui314/chibicc/commit/c61c0d00252a8704ff2731f6a57bad3657b84170).
Earlier explanations are available in Git history.

`#line` now adjusts subsequent token line numbers and optionally changes the name
used by `__FILE__`. Its arguments undergo macro expansion first. Tokens snapshot
the current file delta while preprocessing so later markers cannot change the
line numbers of earlier tokens. Physical file paths still control include lookup.

```sh
printf '#line 41 "virtual.c"\nint main(void){return __LINE__;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The macro becomes the integer 42; assembly loads that constant and returns it.
Debug `.loc` line numbers use the recorded delta. This original version applies
the marker number to the directive's line, so the following line is one larger;
we intentionally retain that historical off-by-one behavior. Diagnostics still
show the physical filename at this step, even when `__FILE__` uses a logical one.
Tests cover markers with and without filenames, macro arguments, token snapshots,
diagnostics, invalid marker types and the original new line.c fixture.
Python gives raw source tokens a File object too, enabling the same tracking in
parser tests; C always tokenizes through a File. Filename bytes decode as UTF-8.

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
