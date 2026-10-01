# Lesson 292: Choose dependency targets with -MT

Original chibicc commit: [`db850f37a2a284bf18cea427e4676a22d83d04b8`](https://github.com/rui314/chibicc/commit/db850f37a2a284bf18cea427e4676a22d83d04b8).
Earlier explanations are available in Git history.

-MT TARGET replaces the default basename.o target in a -M dependency rule. Repeating
-MT joins the target strings with spaces, producing a rule for several targets.
The supplied strings are written literally; this commit does not escape Make
syntax. -MF selects the output file and -MP still adds dummy header rules.

```sh
printf '#define ANSWER 42\n' > /tmp/lesson-answer.h
printf '#include "lesson-answer.h"\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -M -MP -MF /tmp/lesson.d -MT build/lesson.o -MT lesson-copy.o /tmp/lesson.c
cat /tmp/lesson.d
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The dependency rule begins build/lesson.o lesson-copy.o: and lists the source and
header. The header also gets an empty rule. These options affect build metadata;
normal assembly loads 42 into rax and returns, and echo $? displays the exit status.
Tests check single and repeated targets, an empty literal target and missing -MT
arguments, alongside -M, -MF and -MP behavior. Python uses None for an absent target
and immutable string concatenation instead of C's allocated formatted strings.
Earlier lesson explanations remain in Git history; README describes this lesson.

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
