# Lesson 119: GNU alignment queries on expressions

Original chibicc commit: [`310a87e15e98bb5abfd86ea7bb2a1cca1f5243c7`](https://github.com/rui314/chibicc/commit/310a87e15e98bb5abfd86ea7bb2a1cca1f5243c7).
Earlier explanations are available in Git history.

## What changed

_Alignof now accepts a unary expression, with or without parentheses, as a GNU
extension. The parser annotates its operand's type and replaces the entire query
with a numeric node. The type-name form retains its special parsing path.

The operand is parsed but never executed: `_Alignof(++x)` does not increment x,
and `_Alignof f()` emits no call. Upstream queries operand.ty.align, so an object's
_Alignas override does not affect this result in this historical step. Python
uses the same type annotation and numeric-node construction.

## Assembly and WSL example

```sh
printf 'int main(){int x=0;int y=_Alignof(++x);return x+y;}\n' > /tmp/lesson119.c
python3 python/main.py /tmp/lesson119.c > /tmp/lesson119.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson119 /tmp/lesson119.s
/tmp/lesson119
echo $?
```

The query becomes `mov $4, %rax` while initializing y. No increment of x appears
in the assembly, and exit status is 4. Tests cover both expression spellings,
unevaluated increments and calls, overridden objects, emitted constants, real
execution, and updated original alignof examples.

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
