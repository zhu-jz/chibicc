# Lesson 72: _Bool values and conversions

Original chibicc commit: [`44bba965cbe3827be2b68651e541b33fa040bb72`](https://github.com/rui314/chibicc/commit/44bba965cbe3827be2b68651e541b33fa040bb72).
Earlier explanations are available in Git history.

## What changed

_Bool is a one-byte integer type whose conversions normalize values: zero becomes
0, every nonzero value becomes 1. Char conversion instead keeps the low byte, so
(char)256 is 0 while (_Bool)256 is 1. Assignment, explicit casts, function
arguments, and returns all use the shared conversion path. Arithmetic promotes
_Bool to int. Zero comparisons inspect eax for small integers and rax for longs
or pointers, following the original helper.

Python represents BOOL as another Type kind; no Python bool evaluation performs
compiled arithmetic. Conversion is emitted as machine instructions.

## Assembly and WSL example

```sh
printf 'int main(){_Bool x=256;return x;}\n' > /tmp/lesson72.c
python3 python/main.py /tmp/lesson72.c > /tmp/lesson72.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson72 /tmp/lesson72.s
/tmp/lesson72
echo $?
```

`cmp $0, %eax`, `setne %al`, and `movzx %al, %eax` create exactly 0 or 1 before
storing a byte. The example exits with 1. Tests cover zero/nonzero values,
pointers, long values whose low 32 bits are zero, argument/return conversion,
promotion, assembly widths, and the updated original programs.

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
