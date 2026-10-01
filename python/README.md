# Lesson 109: Braces around scalar initializers

Original chibicc commit: [`a58958ccb40a127a83e3383ef3887e4721352238`](https://github.com/rui314/chibicc/commit/a58958ccb40a127a83e3383ef3887e4721352238).
Earlier explanations are available in Git history.

## What changed

A scalar initializer can now be surrounded by braces, including repeated nested
braces: `int x={{{42}}};`. The parser recursively unwraps each brace pair and
stores the same assignment expression. This applies to pointer initializers too,
so a global braced pointer still becomes a relocation.

The Python recursion directly follows the C parser. Empty scalar braces and
multiple scalar values still produce errors, as do trailing commas at this step.
No new expression or assembly operation is required.

## Assembly and WSL example

```sh
printf 'int main(){int x={42};return x;}\n' > /tmp/lesson109.c
python3 python/main.py /tmp/lesson109.c > /tmp/lesson109.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson109 /tmp/lesson109.s
/tmp/lesson109
echo $?
```

Assembly clears the local int and stores 42 just as for an unbraced initializer.
Main loads x and returns exit status 42. Tests cover repeated braces, globals,
array elements, pointer relocations, malformed scalar lists, emitted assembly,
and the original initializer program.

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
