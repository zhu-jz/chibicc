# Lesson 279: Link archive and shared-library files

Original chibicc commit: [`d56dd2f46e4049f017eae0dc99b2d16e78b88bee`](https://github.com/rui314/chibicc/commit/d56dd2f46e4049f017eae0dc99b2d16e78b88bee).
Earlier explanations are available in Git history.

The driver recognizes .a archives and .so shared libraries and forwards them to ld
along with object files. Explicit -x language selection now takes precedence over
all suffixes, including .o; -xnone restores suffix detection. Library order remains
the input order, which matters when extracting members from static archives.

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson-helper.c
printf 'int answer(void);int main(void){return answer();}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -c -o /tmp/lesson-helper.o /tmp/lesson-helper.c
ar rcs /tmp/lesson-helper.a /tmp/lesson-helper.o
gcc -o /tmp/lesson /tmp/lesson.s /tmp/lesson-helper.a
/tmp/lesson
echo $?  # 42
python3 python/main.py -o /tmp/lesson /tmp/lesson.c /tmp/lesson-helper.a
```

Assembly calls the external answer function; the linker supplies its definition
from the archive. Tests link and run both archive and shared-library inputs and
check that -xc can interpret a text source named .o. GCC builds the separate helper
fixture, while our Python compiler translates main. Python uses string file kinds
instead of C's enum, preserving this commit's classification order.

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
