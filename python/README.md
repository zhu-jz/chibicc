# Lesson 297: Cache successful include-file searches

Original chibicc commit: [`c0f0614e6b7647fd4703abf4c455024c2ade8cd7`](https://github.com/rui314/chibicc/commit/c0f0614e6b7647fd4703abf4c455024c2ade8cd7).
Earlier explanations are available in Git history.

Include-path searches now remember successful filename resolutions. Repeating a
search can return the saved path without testing each directory again. Absolute
paths still bypass the search, and missing files are not cached, so a later search
can find a newly created file.

```sh
printf '#define ANSWER 42\n' > /tmp/lesson-answer.h
printf '#include <lesson-answer.h>\n#include <lesson-answer.h>\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -I/tmp -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The second include reuses the successful search; it still reads and preprocesses
the header again. This is path-search caching, not an include guard. Assembly
still returns 42. Tests count filesystem probes, verify cache hits, and confirm
that misses are retried. Python keys the cache by filename plus the include-path
tuple, so separate in-process compilations with different search lists remain
independent; C's process-local cache keys only by filename. Positive results remain
cached if the file later disappears, following the original caching behavior.

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
