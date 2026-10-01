# Lesson 174: Test empty macro arguments

Original chibicc commit: [`dd4306cdd8158f76f094fc699530311228536adb`](https://github.com/rui314/chibicc/commit/dd4306cdd8158f76f094fc699530311228536adb).
Earlier explanations are available in Git history.

This original commit changes only the macro test program. The existing reader
already represents an empty argument as an EOF-only token sequence, so
substituting it contributes no tokens to the replacement body. No compiler
implementation change is needed in Python either.

```sh
printf '#define JOIN(x,y) x y\nint main(void){return JOIN(,4+5);}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 9
```

The empty first argument disappears, leaving `4+5`. Assembly adds those values
and returns 9 in `%rax`. New tests cover an empty first or last argument, two
empty arguments in an unused parameter list, and a macro that expands to empty
inside an argument. The original new fixture is copied verbatim and compiled.

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
