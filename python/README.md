# Lesson 93: Switch and case statements

Original chibicc commit: [`044d9ae07ba700c52d8342e4eee26e07eea11619`](https://github.com/rui314/chibicc/commit/044d9ae07ba700c52d8342e4eee26e07eea11619).
Earlier explanations are available in Git history.

## What changed

A switch evaluates its condition once, compares it with each recorded case value,
and jumps to a case, default, or the switch's exit. Case labels emit sequentially,
so execution falls through until a break or return. The parser saves/restores its
current switch and break target for nesting. Continue still targets an enclosing
loop, since switch does not change the continue target.

Python lists replace the case linked list. Numeric case tokens are explicitly
converted to signed 32-bit values to match the original C int field, including
0xffffffff becoming -1. This commit accepts numeric tokens rather than general
constant expressions; duplicate-case/default validation is still incomplete.

## Assembly and WSL example

```sh
printf 'int main(){switch(1){case 0:return 3;case 1:return 42;default:return 7;}}\n' > /tmp/lesson93.c
python3 python/main.py /tmp/lesson93.c > /tmp/lesson93.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson93 /tmp/lesson93.s
/tmp/lesson93
echo $?
```

`cmp $1, %eax` and `je .L..N` select the matching label; a long condition uses
rax instead. The selected return exits with 42, which the shell displays. Tests
cover matching/default/missing cases, fallthrough, signed case conversion,
nested switches, loop continue behavior, assembly widths, stray labels, and all
updated original C programs.

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
