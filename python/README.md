# Lesson 294: Quote Make dependency targets with -MQ

Original chibicc commit: [`7aa72e41e6b2703b3f357507252008ebe25dc08d`](https://github.com/rui314/chibicc/commit/7aa72e41e6b2703b3f357507252008ebe25dc08d).
Earlier explanations are available in Git history.

-MQ selects a dependency target like -MT, but quotes characters significant to Make.
Dollar signs become $$, # becomes \#, and spaces/tabs gain a backslash. Backslashes
immediately before whitespace are duplicated so Make preserves them. Repeated -MQ
and -MT arguments share the target list. Default targets and -MP dummy targets are
also quoted; prerequisite paths are still printed literally in this original step.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -M -MQ 'build file$#.o' -MF /tmp/lesson.d /tmp/lesson.c
cat /tmp/lesson.d
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The rule starts with build\ file$$\#.o:. The assembly is unaffected and returns 42.
Tests check quoting, preceding backslashes, mixed target options and a real Make
parse of the quoted target. Python builds a string list instead of C's allocated
buffer. It also checks for a missing -MQ argument instead of C's unchecked access.

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
