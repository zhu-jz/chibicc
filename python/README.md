# Lesson 111: Uninitialized globals in BSS

Original chibicc commit: [`3d216e3e06eee7ea3679503867a619c28458e8a7`](https://github.com/rui314/chibicc/commit/3d216e3e06eee7ea3679503867a619c28458e8a7).
Earlier explanations are available in Git history.

## What changed

Uninitialized globals now use the .bss section and .zero directives. The loader
provides their zero-filled memory without storing all those zero bytes in the
object file. Globals with explicit initializers use .data, even when their
initializer evaluates to zero. Linker-resolved pointers still use .data.

The Python check uses `init_data is not None`, rather than byte-buffer truthiness,
matching the distinction between C's null and allocated data pointers. Section
selection is the only compiler change; expression parsing is unchanged.

## Assembly and WSL example

```sh
printf 'int x;int y=42;int main(){return x+y;}\n' > /tmp/lesson111.c
python3 python/main.py /tmp/lesson111.c > /tmp/lesson111.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson111 /tmp/lesson111.s
/tmp/lesson111
echo $?
```

The emitter writes x in .bss with `.zero 4`, and y in .data with four bytes.
Main loads both and returns 42. Tests check initialized-zero versus uninitialized
objects, array zeroing, emitted sections, B/D symbol types in the assembled object
using nm from build-essential, actual execution, and original C examples.

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
