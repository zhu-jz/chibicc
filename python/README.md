# Lesson 78: Prefix increment and decrement

Original chibicc commit: [`47f19371f75db9029ea1b8b3783624fb7838d2db`](https://github.com/rui314/chibicc/commit/47f19371f75db9029ea1b8b3783624fb7838d2db).
Earlier explanations are available in Git history.

## What changed

Prefix ++ and -- parse a unary operand and reuse compound-assignment lowering:
++x becomes x+=1, --x becomes x-=1. They return the updated value, preserve the
destination type, evaluate its address once, and scale pointer updates by the
element size. sizeof parses and types these expressions without executing them.
Postfix forms are not part of this commit.

Python reuses the same helper and Node constructors as the prior lesson. The
emitter remains unchanged; introducing a syntax feature does not always require
new assembly operations.

## Assembly and WSL example

```sh
printf 'int main(){int x=41;return ++x;}\n' > /tmp/lesson78.c
python3 python/main.py /tmp/lesson78.c > /tmp/lesson78.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson78 /tmp/lesson78.s
/tmp/lesson78
echo $?
```

The saved address is dereferenced, `add %edi, %eax` adds one, and a store updates
x before main returns 42. Tests cover both prefix forms, pointer movement,
side-effecting targets, sizeof suppression, invalid lvalues, assembly, and the
updated original arithmetic and sizeof fixtures.

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
