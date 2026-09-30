# Lesson 54: Unions and overlapping storage

Original chibicc commit: [`11e3841832697c8ba4a1d68f5daa05045f70a716`](https://github.com/rui314/chibicc/commit/11e3841832697c8ba4a1d68f5daa05045f70a716).
Earlier explanations are available in Git history.

## What changed

`union` shares struct's member parser, tag namespace, scope lookup and member
access syntax. The layout differs: every member's offset is zero, alignment
is the maximum member alignment, and size is the largest member size rounded
up to that alignment. `union {int a; char b[9];}` therefore has size 16 and
alignment 8 at this stage. An empty union has size 0 and alignment 1.

Members overlap instead of occupying successive regions. On x86-64 Linux,
storing 515 into the eight-byte int a writes bytes 3, 2, 0, 0, ... in
little-endian order. Reading b[0] or b[1] observes 3 or 2. This machine-specific
view is what upstream's new tests demonstrate.

The existing MEMBER codegen works for unions without new instructions. Python
keeps the same Type/Member dataclasses and lists; a shared parser avoids
repeating the member grammar. Tags become visible only after member parsing,
and tag-kind validation remains incomplete as in this commit. Aggregate
copying and aggregate function calling are still not implemented.

## Assembly and WSL example

```sh
printf 'int main(){union {int a;char b[4];} x;x.a=515;return x.b[0]+x.b[1];}\n' > /tmp/lesson54.c
python3 python/main.py -o /tmp/lesson54.s /tmp/lesson54.c
cat /tmp/lesson54.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson54 /tmp/lesson54.s
/tmp/lesson54
echo $?
```

The int store writes `%rax` to the union's address. Member offsets add zero,
then char subscripts select bytes and `movsbq` loads them. Adding the bytes
returns 5; the executable prints nothing and the shell displays status 5.
Tests inspect overlap, size rounding, nested struct/union layout, global and
tagged unions, arrow access, and array stride, and run the new upstream union
fixture together with all existing C fixtures.

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
