# Lesson 211: Initialize global struct bitfields

Original chibicc commit: [`441a89b80babf98d3feb13e4594ee01eb6cc4dd5`](https://github.com/rui314/chibicc/commit/441a89b80babf98d3feb13e4594ee01eb6cc4dd5).
Earlier explanations are available in Git history.

Global initializer serialization now merges each struct bitfield's masked
constant into its storage unit. Other members retain their ordinary byte
serialization. Uninitialized fields remain zero. Python reads and writes the
little-endian buffer with int.from_bytes and to_bytes instead of C casts to
integer pointers, avoiding dependence on the host's alignment or byte order.

```sh
printf 'struct T{unsigned int a:6,b:4;}g={42,7};int main(void){return g.a;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The data section contains the packed initial word. Main loads it and shifts
to isolate a, leaving 42 in rax. Tests inspect exact initializer bytes and run
signed fields, zero-filled trailing fields, arrays and original fixtures.
The original stops processing struct members at the first absent bitfield
initializer; that historical rule is retained. Union serialization is unchanged.

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
