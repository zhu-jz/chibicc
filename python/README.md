# Lesson 33: Signed char values

Original chibicc commit: [`be38d63d1b9cd236ef3ec884eedad8112bb6e6f9`](https://github.com/rui314/chibicc/commit/be38d63d1b9cd236ef3ec884eedad8112bb6e6f9).
Earlier explanations are available in Git history.

## What changed

The new `char` type occupies one byte; int and pointers remain eight bytes.
Declarations, parameters, arrays, globals, and pointer arithmetic use its size.
A char store emits `mov %al,(%rdi)`, writing only the low byte. A char load emits
`movsbq (%rax),%rax`, sign-extending that byte, so storing 255 and reading it
produces -1. Arrays of chars advance one byte per element.

Char parameters are saved with `%dil`, `%sil`, `%dl`, `%cl`, `%r8b`, and `%r9b`.
Calls still pass register values in their 64-bit forms; the callee selects the
appropriate store width. Locals use consecutive sized slots, with the total
frame aligned to 16 bytes; individual mixed slots may be unaligned on x86-64.

## Run it

```sh
python3 python/main.py 'int main(){char x=255; return x<0;}' > /tmp/lesson33.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson33 /tmp/lesson33.s
/tmp/lesson33
echo $?
```

The executable prints nothing; the last command shows **1**. Use an interactive
shell without `set -e` for nonzero statuses. Tests cover all upstream char
examples, signed loads, byte truncation, neighbouring storage, arrays, globals,
and all six char parameter registers. This stage has no full integer promotion
or assignment conversion system: storing truncates, but an assignment expression
can still retain its untruncated register value. These limits follow upstream.
Python does not simulate byte arithmetic; emitted instructions perform it.

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
