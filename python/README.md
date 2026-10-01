# Lesson 248: Expand file modification timestamps

Original chibicc commit: [`922604ae1e29fd1283fcc557e294a7272116c094`](https://github.com/rui314/chibicc/commit/922604ae1e29fd1283fcc557e294a7272116c094).
Earlier explanations are available in Git history.

The GNU `__TIMESTAMP__` macro now becomes a 24-character string describing the
physical file's last modification time in local time. Failed file lookup, such
as standard input, yields the original placeholder `??? ??? ?? ??:??:?? ????`.
A logical filename set by `#line` does not change the file used for this lookup.

```sh
printf 'int main(void){return sizeof(__TIMESTAMP__)+17;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The timestamp occupies 25 bytes including its terminator. `sizeof` becomes 25,
so assembly adds 17 and returns 42. Tests set known file times, check the stdin
placeholder, and verify macro definitions in headers use the defining file's
mtime, matching this original handler's lack of origin traversal.
Python uses os.stat and time.ctime; C uses stat and ctime_r. Both format local
time. Original C fixtures include a runtime length check for the new macro.

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
