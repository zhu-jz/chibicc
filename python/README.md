# Lesson 104: Local union initializers

Original chibicc commit: [`483b194a80e904c11c5c6d855303596145adacee`](https://github.com/rui314/chibicc/commit/483b194a80e904c11c5c6d855303596145adacee).
Earlier explanations are available in Git history.

## What changed

Union initializers now use braces containing one initializer for the first
member. Every member shares offset zero; the first member's type determines
which stores are generated. A nested struct or array member uses its existing
initializer machinery. The entire union is zeroed first, including bytes beyond
that first member.

Children are stored in Python lists as for structs. An empty member list gives
a diagnostic instead of upstream's null-pointer dereference. This historical
step requires exactly one initializer: empty braces, extra elements, and union
copy initializers are not supported. Ordinary union assignment still works.

## Assembly and WSL example

```sh
printf 'int main(){union T{int a;char b[4];} x={0x01020304};return x.b[0];}\n' > /tmp/lesson104.c
python3 python/main.py /tmp/lesson104.c > /tmp/lesson104.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson104 /tmp/lesson104.s
/tmp/lesson104
echo $?
```

The emitter zeroes four bytes and stores 0x01020304 at the union address. On
x86-64's little-endian layout the first byte is 4, the exit status. Tests verify
byte order, nested struct initialization, wider-union zeroing, member store
width, unsupported syntax, and the original initializer examples.

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
