# Lesson 293: Write dependencies during compilation with -MD

Original chibicc commit: [`fb5cfe5d17fd0c0cbc0d17789c065b9bb86ba3c4`](https://github.com/rui314/chibicc/commit/fb5cfe5d17fd0c0cbc0d17789c065b9bb86ba3c4).
Earlier explanations are available in Git history.

-MD writes a dependency rule after preprocessing, then continues parsing and
compiling. -M still stops after dependency output. -MF takes precedence when
choosing a dependency file; otherwise -MD replaces the output name or source name
with a .d suffix. Existing -MT and -MP options also apply to the generated rule.

```sh
printf '#include <stddef.h>\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -MD -MF /tmp/lesson.d -o /tmp/lesson.s /tmp/lesson.c
cat /tmp/lesson.d
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly still defines main and returns 42 in rax. The extra .d file lists its
source and included header for Make. Tests compile two files with -c -MD, check
their real ELF objects and separate dependency files, and combine -S with -MF.
As in C, the default .d name uses only the basename and is written in the current
working directory. Python uses explicit option arguments rather than C globals.
Dependencies are written before parsing, so a later syntax error can leave a .d file.

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
