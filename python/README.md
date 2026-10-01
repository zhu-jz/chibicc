# Lesson 117: Extern declarations inside blocks

Original chibicc commit: [`27647455e4cb7db1545a7b69c3a324aa025a471a`](https://github.com/rui314/chibicc/commit/27647455e4cb7db1545a7b69c3a324aa025a471a).
Earlier explanations are available in Git history.

## What changed

Compound statements now route function declarations and extern variable
declarations through the global-object parser. Their names are bound in the
current block scope, but they allocate no local stack slots or data definitions.
Leaving the block removes those name bindings. Ordinary declarations still
allocate locals and create initializer statements.

Python reuses the existing parsers and Scope objects, as upstream reuses its
global-object routines and linked scope records. This commit does not add broader
redeclaration checking. Block function prototypes work with or without extern.

## Assembly and WSL example

```sh
printf 'int main(){extern int g;int f(int x);return f(g);}\n' > /tmp/lesson117.c
printf 'int g=42;int f(int x){return x;}\n' > /tmp/lesson117-helper.c
python3 python/main.py /tmp/lesson117.c > /tmp/lesson117.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson117 /tmp/lesson117.s /tmp/lesson117-helper.c
/tmp/lesson117
echo $?
```

Main loads external g and passes it in edi to f, with no local g slot or emitted
g storage. Exit status is 42. Tests check variable and function declarations,
external linking, block shadowing, restored outer names, zero local slots,
assembly calls, escaped-scope rejection, and original extern examples.

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
