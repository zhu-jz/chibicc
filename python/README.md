# Lesson 56: Four-byte ints

Original chibicc commit: [`5831edaab3eb6d56126c08f01f5639222602f7e5`](https://github.com/rui314/chibicc/commit/5831edaab3eb6d56126c08f01f5639222602f7e5).
Earlier explanations are available in Git history.

## What changed

Int now has size and alignment 4, matching x86-64 Linux C. Char stays one byte
and pointers stay eight. This changes sizeof, pointer-arithmetic scaling,
array strides, struct/union layouts, local offsets, and global zero storage.
An `int[3]` occupies 12 bytes; `struct {char a;int b;}` has offsets 0 and 4
and total size 8.

An int store uses `%eax`, writing only the low four bytes. An int load uses
`movsxd (%rax), %rax`, sign-extending those four bytes into the expression
register. Parameter saves choose eight-bit, thirty-two-bit, or sixty-four-bit
argument-register names for sizes 1, 4, or 8. Unsupported sizes produce a
source diagnostic in Python instead of C's internal unreachable error.

This original commit changes memory widths, not all arithmetic conversions.
Expressions still use sixty-four-bit arithmetic registers; storing into an int
truncates to four bytes, and reloading makes the stored sign visible. Function
return conversion, full type compatibility, and aggregate call ABI rules remain
incomplete. Python's compile-time integers are arbitrary precision, but the
emitted memory operations implement the target's four-byte values.

## Assembly and WSL example

```sh
printf 'int main(){int x=42;return x;}\n' > /tmp/lesson56.c
python3 python/main.py -o /tmp/lesson56.s /tmp/lesson56.c
cat /tmp/lesson56.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson56 /tmp/lesson56.s
/tmp/lesson56
echo $?
```

x now lives at -4(%rbp) within a sixteen-byte frame. `mov %eax, (%rdi)` stores
42 without overwriting a neighboring int, and `movsxd (%rax), %rax` loads it
for the return. The shell displays status 42. Tests update the previous layout
and sizeof expectations, check signed loads, truncation and neighboring values,
mixed-size parameters, and an int array passed to a tiny GCC-built helper.
The updated upstream C fixtures and the full Python regression suite are run.

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
