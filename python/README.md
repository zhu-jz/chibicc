# Lesson 254: Derive a declaration type with typeof

Original chibicc commit: [`7d80a5136d1b2926dd0776c51896c40723c518c5`](https://github.com/rui314/chibicc/commit/7d80a5136d1b2926dd0776c51896c40723c518c5).
Earlier explanations are available in Git history.

GNU `typeof(...)` now accepts a type name or an expression. The parser attaches
types to the expression and reuses its type for the declaration; it does not
emit code to evaluate that expression. Arrays keep their array type here rather
than decaying to a pointer. The predefined __typeof__ alias now works too.

```sh
printf 'int main(void){int x=42;typeof(x++) y=0;return x+y;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly initializes x and y and adds their values. There is no increment of x
from typeof's operand, so the returned value stays 42. Tests cover type-name and
expression forms, pointers, arrays, string arrays, floating types, the alias,
syntax errors and the original new typeof.c fixture.
Python returns the selected Type object with a token index; C returns a pointer
and updates its rest pointer. Variable-length arrays are not introduced by this
commit, so their special evaluation rules are not claimed.

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
