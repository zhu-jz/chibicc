# Lesson 88: Incomplete structs and unions

Original chibicc commit: [`61a10551209a0d3770449862152e1b73b584d771`](https://github.com/rui314/chibicc/commit/61a10551209a0d3770449862152e1b73b584d771).
Earlier explanations are available in Git history.

## What changed

An unknown tagged struct/union creates an incomplete type with size -1. Pointers
to it are valid; a later definition completes the existing object in the current
scope. This makes forward references, typedef aliases, and self-referential
members work. Definitions in an inner scope create distinct types rather than
changing outer types. Local incomplete objects still produce an error.

Python replaces the fields on the existing Type object, equivalent to C's
`*old=*new`, so pointers keep seeing that same object. Aggregate declarators now
retain the shared type rather than copying it for name metadata. This is needed
for typedef struct T T to see T's completion; builtin types still copy declaration
names. Strict redefinition/tag-kind validation remains incomplete in this commit.

## Assembly and WSL example

```sh
printf 'struct T{struct T *next;int x;};int main(){struct T a,b;b.x=42;a.next=&b;return a.next->x;}\n' > /tmp/lesson88.c
python3 python/main.py /tmp/lesson88.c > /tmp/lesson88.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson88 /tmp/lesson88.s
/tmp/lesson88
echo $?
```

next is an eight-byte pointer; x lies at offset eight. Address calculation stores
b's address in a.next, and the final member load follows that pointer and reads
b.x. The shell displays 42. Tests cover forward pointer identity, self references,
union completion, typedef completion, incomplete local errors, sizeof, assembly,
and updated original struct programs.

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
