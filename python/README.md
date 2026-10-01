# Lesson 133: Wide pointer differences and size queries

Original chibicc commit: [`8b8f3de48bba31ccfa84e3573075b2125bc130c3`](https://github.com/rui314/chibicc/commit/8b8f3de48bba31ccfa84e3573075b2125bc130c3).
Earlier explanations are available in Git history.

## What changed

Pointer subtraction now produces signed long before dividing by element size,
retaining all 64 address bits. sizeof and _Alignof produce unsigned long numeric
nodes, for both type and expression forms. Their shifts and arithmetic consequently
use eight-byte unsigned operations rather than four-byte int operations.

Python supplies explicit types on these numeric and subtraction nodes, matching
upstream new_ulong and long pointer-difference annotations. Type sizes themselves
remain Python integers; this change describes the generated C expression type.

## Assembly and WSL example

```sh
printf 'int main(void){return sizeof(char)<<63>>63;}\n' > /tmp/lesson133.c
python3 python/main.py /tmp/lesson133.c > /tmp/lesson133.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson133 /tmp/lesson133.s
/tmp/lesson133
echo $?
```

The size one shifts to the top bit with shl on rax, then shr shifts in zeros and
returns it to one. Exit status is 1. Tests check query result types, nested sizeof,
64-bit logical shifts, pointer differences beyond 32 bits without dereferencing
those addresses, signed comparisons, emitted widths, and original C examples.

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
