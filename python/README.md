# Lesson 290: Choose a dependency output file with -MF

Original chibicc commit: [`95d5a46234f98f3793c965bebe036361cbb1978e`](https://github.com/rui314/chibicc/commit/95d5a46234f98f3793c965bebe036361cbb1978e).
Earlier explanations are available in Git history.

-MF FILE selects the destination for -M dependency text. It takes precedence over
-o, otherwise the previous -o or stdout behavior remains. -MF by itself does not
enable dependency generation. The original accepts a separate argument, and a
missing argument is diagnosed before processing input files.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -M -MF /tmp/lesson.d /tmp/lesson.c
cat /tmp/lesson.d
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The dependency file contains a lesson.o rule pointing at /tmp/lesson.c. Normal
compilation still emits a main function returning 42. Tests check destination
selection over -o, -MF - for stdout and a missing argument, plus existing -M tests.
Python passes the selected option explicitly to cc1 instead of C's global pointer;
an omitted option is None, while the literal '-' means stdout as before.

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
