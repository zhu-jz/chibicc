# Lesson 256: Select an expression by its type

Original chibicc commit: [`1faab48ecf83d31a4fd781f10f6f00acb681d2dd`](https://github.com/rui314/chibicc/commit/1faab48ecf83d31a4fd781f10f6f00acb681d2dd).
Earlier explanations are available in Git history.

C11 `_Generic` now parses a controlling expression and a list of typed
associations. It uses the previous lesson's compatibility check to choose one
expression during parsing; arrays and functions in the control become pointer
types. Only the selected expression appears in the executable syntax tree.

```sh
printf 'int main(void){int x=42;return _Generic(x++,int:x,default:x++);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly initializes x and loads it for the return. Neither the controlling
increment nor the unselected default increment executes. Tests cover numeric,
array and function controls, default ordering, missing matches, discarded side
effects and the original generic.c fixture.
Python keeps the selected Node reference instead of a nullable C pointer. This
original parser does not reject duplicate compatible associations: the last
matching one wins. That historical behavior is preserved and tested.

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
