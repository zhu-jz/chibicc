# Lesson 305: Pass individual linker arguments with -Xlinker

Original chibicc commit: [`469f159bb1adebb92ca2c9a7841466a98e6ad956`](https://github.com/rui314/chibicc/commit/469f159bb1adebb92ca2c9a7841466a98e6ad956).
Earlier explanations are available in Git history.

-Xlinker ARG passes one argument unchanged to ld through the extra-linker-argument
list. Repeat it for options needing a separate value, such as -Xlinker -Map
-Xlinker report.txt. Spaces and commas inside an argument remain part of that
argument. A missing argument is detected before file processing.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -Xlinker --gc-sections -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
python3 python/main.py -Xlinker --gc-sections -o /tmp/lesson /tmp/lesson.c
```

The assembly still returns 42. The driver passes --gc-sections to the linker as
one argument. Tests generate a real link map at a filename containing both a
space and comma, run the executable and check a missing argument. Python appends
the string directly to a subprocess list, corresponding to C's StringArray.
The original driver fixture uses native cc; the Python tests exercise our driver.

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
