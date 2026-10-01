# Lesson 97: Local array initializers

Original chibicc commit: [`22dd560ecf06e9ac4a4c1be33be74bac7924f06a`](https://github.com/rui314/chibicc/commit/22dd560ecf06e9ac4a4c1be33be74bac7924f06a).
Earlier explanations are available in Git history.

## What changed

Local initializers now have an intermediate tree: arrays contain child
initializers, while each scalar leaf holds an expression. A designation path
identifies a local variable and its nested element indices. The parser lowers
this tree into assignments joined by comma expressions, in increasing element
order. Thus `int a[2][2]={{1,2},{3,4}}` becomes assignments to each a[row][column].
The new NULL_EXPR node starts an empty assignment chain and emits no instructions.
Scalar initializers and struct-copy expressions use the same lowering path.

Python dataclasses and lists replace C's initializer nodes, child-pointer arrays,
and linked designation paths. This commit requires exactly the declared number
of array elements with braces at every array level. Partial lists, trailing
commas, string initialization, and incomplete-length deduction remain unsupported.

## Assembly and WSL example

```sh
printf 'int main(){int a[3]={1,2,42};return a[2];}\n' > /tmp/lesson97.c
python3 python/main.py /tmp/lesson97.c > /tmp/lesson97.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson97 /tmp/lesson97.s
/tmp/lesson97
echo $?
```

Each element address is computed with scaled pointer arithmetic, then
`mov %eax, (%rdi)` stores a four-byte int. The final load returns 42, which the
shell displays. Tests cover nested arrays, left-to-right initializer effects,
char conversion, pointer elements, lowered tree shape, assembly, this stage's
list restrictions, and the new original initializer program.

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
