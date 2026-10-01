# Lesson 121: Compound literals

Original chibicc commit: [`127056dc1de6ddad280f6cf09cb15538dca22f43`](https://github.com/rui314/chibicc/commit/127056dc1de6ddad280f6cf09cb15538dca22f43).
Earlier explanations are available in Git history.

## What changed

`(type){initializer}` now creates an unnamed object. At file scope it becomes
anonymous global data, allowing nested pointer relocations. Inside a block it
becomes a local initialized object; a comma node sequences initialization before
returning that object's value or address. Compound literals are lvalues, so they
can be assigned to or addressed.

The cast parser distinguishes a following brace and hands the expression back
to unary/postfix parsing. Python checks scope-list length where upstream checks
the outer scope link, then reuses existing initializer lowering. This historical
postfix path returns early: wrap the literal in parentheses before applying a
subscript or member suffix, as the original tests do.

## Assembly and WSL example

```sh
printf 'int *p=&(int){42};int main(){return *p;}\n' > /tmp/lesson121.c
python3 python/main.py /tmp/lesson121.c > /tmp/lesson121.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson121 /tmp/lesson121.s
/tmp/lesson121
echo $?
```

Assembly emits an anonymous int containing 42 and a .quad relocation from p to
that object. Main follows the pointer and returns 42. Local literals instead
emit stack zeroing and stores. Tests check scalar, array and struct values,
runtime local initial values, writable literal storage, global relocations,
nested pointer trees, assembly, and the new original compound-literal program.

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
