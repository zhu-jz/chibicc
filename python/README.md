# Lesson 106: Global struct initializers

Original chibicc commit: [`eeb62b6dd547da5742f3ed74f8c8ae534d883dd9`](https://github.com/rui314/chibicc/commit/eeb62b6dd547da5742f3ed74f8c8ae534d883dd9).
Earlier explanations are available in Git history.

## What changed

Global initializer serialization now descends through struct members. Each
member's initializer is written at its aligned offset; the initial zero-filled
buffer preserves omitted members and padding. Array recursion and struct
recursion combine naturally for nested aggregates.

Python keeps the same member indices and offsets as upstream and writes into a
bytearray. Global union serialization and address relocations remain incomplete.
Global struct copy expressions are not evaluated by this historical serializer;
use brace lists for global struct initialization at this step.

## Assembly and WSL example

```sh
printf 'struct T{char a;int b;} g={1,42};int main(){return g.b;}\n' > /tmp/lesson106.c
python3 python/main.py /tmp/lesson106.c > /tmp/lesson106.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson106 /tmp/lesson106.s
/tmp/lesson106
echo $?
```

The .data section stores byte 1, three padding zeros, then the four-byte value
42. Main adds offset four and loads g.b, yielding exit status 42. Tests check
exact bytes, nested structs, arrays of structs, partial initialization, emitted
data, real execution, and the original expanded initializer program.

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
