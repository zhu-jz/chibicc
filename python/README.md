# Lesson 289: Emit Make dependencies with -M

Original chibicc commit: [`d0c4667b6bccf35ddf069c777689cd18c6a632b3`](https://github.com/rui314/chibicc/commit/d0c4667b6bccf35ddf069c777689cd18c6a632b3).
Earlier explanations are available in Git history.

-M stops after preprocessing and prints a Make rule listing the source and every
opened include file. The target is the source basename with an .o suffix. Each
prerequisite appears on a continued line. -o redirects this dependency text; -M
takes precedence over -E. Parsing and assembly generation are skipped in this mode.

```sh
printf '#include <stddef.h>\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -M /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The rule starts with lesson.o and lists /tmp/lesson.c and python/include/stddef.h.
Normal compilation still emits main returning 42; dependency output itself is
text for Make rather than machine instructions. Tests check nested includes,
file order, output redirection, -M/-E precedence and preprocessing invalid C text.
Python uses the existing File list instead of C's global input-file array. This
initial step does not escape special Make characters or deduplicate opened files.

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
