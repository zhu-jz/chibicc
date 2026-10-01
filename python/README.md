# Lesson 249: Remember the main translation unit filename

Original chibicc commit: [`3a10c8aa44250e51dfe33e50b3121d6061faee4b`](https://github.com/rui314/chibicc/commit/3a10c8aa44250e51dfe33e50b3121d6061faee4b).
Earlier explanations are available in Git history.

The GNU `__BASE_FILE__` macro now expands to the original input filename even
inside included headers. Unlike `__FILE__`, it does not change after `#line`.
The driver supplies the current translation unit's path when its internal Python
compiler process initializes predefined macros.

```sh
printf 'int main(void){return __BASE_FILE__[0]==47?42:0;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The absolute input path begins with slash (ASCII 47). Assembly loads its first
byte, compares it and returns 42 for the true branch. Tests distinguish the root
path, header path and logical filename, check stdin and command-line override,
and run the original macro.c assertion using its relative input path.
Python captures the base path in a per-compilation macro handler instead of C's
global base_file. This also keeps independent preprocessing calls isolated.

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
