# Lesson 112: Flexible array member layout

Original chibicc commit: [`824543bb2f2b2e4f445d8c58b32f53bf1eec63ce`](https://github.com/rui314/chibicc/commit/824543bb2f2b2e4f445d8c58b32f53bf1eec63ce).
Earlier explanations are available in Git history.

## What changed

A trailing incomplete array member, as in `struct T{int x;int y[];}`, is now
converted to a zero-length array before layout. It contributes alignment and
an offset but no element storage. sizeof(T) therefore describes only the fixed
part of the object. Other incomplete members are unchanged by this commit.

Python replaces the last member's Type with array_of(base, 0), following the C
implementation. This step handles layout only: it neither allocates additional
space automatically nor initializes a flexible tail. Accessing tail elements
requires actual additional backing storage. The shared member parser also applies
this transformation to unions, matching this historical implementation.

## Assembly and WSL example

```sh
printf 'int main(){return sizeof(struct T{int x;int y[];});}\n' > /tmp/lesson112.c
python3 python/main.py /tmp/lesson112.c > /tmp/lesson112.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson112 /tmp/lesson112.s
/tmp/lesson112
echo $?
```

sizeof is compiled to `mov $4, %rax`; no tail memory is accessed. Exit status is
4. Tests check fixed sizes, alignment, zero-sized member type, member address
offset, BSS allocation size, actual executables, and upstream sizeof examples.

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
