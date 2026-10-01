# Lesson 291: Emit dummy header targets with -MP

Original chibicc commit: [`57c1d4ec0290d49fa1e954ff3e7a51e24d71a3a1`](https://github.com/rui314/chibicc/commit/57c1d4ec0290d49fa1e954ff3e7a51e24d71a3a1).
Earlier explanations are available in Git history.

With -M, -MP appends an empty Make rule for each opened file after the first one.
These dummy targets let Make continue when a previously included header has been
removed, rather than failing because no rule can build that old prerequisite.
-MP alone does not request dependency output, and -MF still chooses its destination.

```sh
printf '#define ANSWER 42\n' > /tmp/lesson-answer.h
printf '#include "lesson-answer.h"\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -M -MP -MF /tmp/lesson.d /tmp/lesson.c
cat /tmp/lesson.d
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The dependency file now includes an empty /tmp/lesson-answer.h: rule. Ordinary
assembly still returns the expanded value 42. Tests generate a rule, remove the
header and ask Make to dry-run the object target; existing dependency tests remain.
Python appends strings where C prints lines. As in the original, the first opened
file is skipped by position, which can be a forced include rather than the source.
These are empty rules, not .PHONY declarations, and filenames are not escaped yet.

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
