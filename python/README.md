# Lesson 27: One-dimensional arrays

Original chibicc commit: [`8b6395d0f2be4024bd7e7921157a6496951eb162`](https://github.com/rui314/chibicc/commit/8b6395d0f2be4024bd7e7921157a6496951eb162).
Earlier explanations are available in Git history.

## What changed

`int x[3];` creates an ARRAY type with element type int, length 3, and size
24 bytes. Types now carry sizes; integers and pointers are still eight bytes.
Local offsets sum each variable's size and the frame rounds up to 16 bytes.

Evaluating an array leaves its address in `%rax`, without a `mov (%rax),%rax`
load. This implements array-to-pointer conversion. Dereference loads a scalar
but leaves an array address unchanged. Whole-array assignment is rejected.
Pointer arithmetic now scales by the base type's size instead of a hardcoded 8.

There is no subscript syntax yet; access elements using `*(x+1)`. Array lengths
must be numeric tokens. At this stage `&x` for an array is typed as a pointer
to its element, matching upstream's simplified behavior.

## Run it

```sh
python3 python/main.py 'int main(){int x[3]; *x=3; *(x+1)=4; *(x+2)=5; return *(x+1);}' > /tmp/lesson27.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson27 /tmp/lesson27.s
/tmp/lesson27
echo $?
```

The last command shows **4**; the executable prints nothing. Use an interactive
shell without `set -e` for nonzero statuses. For this array the generator uses
`lea -24(%rbp),%rax`, adds an eight-byte element offset, and loads the selected
value. A 32-byte frame holds its 24 bytes of storage.

Tests cover all upstream array examples, arrays of pointers, address conversion,
frame size/offsets, invalid sizes, and array assignment. Python's size arithmetic
does not overflow a C int, but emitted frame/immediate sizes still must be
representable by the assembler. Bounds and memory accesses are unchecked.

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
