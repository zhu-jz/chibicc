# Lesson 257: Give function types a GNU sizeof value

Original chibicc commit: [`aee7891acb3e653dcfb10ec4172ae4d099ebf034`](https://github.com/rui314/chibicc/commit/aee7891acb3e653dcfb10ec4172ae4d099ebf034).
Earlier explanations are available in Git history.

Function types now have size and alignment 1. Standard C disallows sizeof on a
function, but this GNU extension gives it the constant value 1. Function pointers
remain ordinary eight-byte pointers; executable function code has no such
one-byte storage limit.

```sh
printf 'int main(void){return sizeof(main)+41;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Parsing replaces sizeof(main) with 1, and the assembly adds 41 before returning.
Tests cover expression and type-name forms, function alignment, pointer size and
the original sizeof.c addition. Python initializes the two Type fields directly;
C uses its new_type constructor. This step changes type metadata, not function
calling conventions or how emitted machine code is measured.

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
