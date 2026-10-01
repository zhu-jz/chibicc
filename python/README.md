# Lesson 132: Integer literal suffixes and types

Original chibicc commit: [`aaf10459d93fb6c0f4539cb792c02a8d15cb0299`](https://github.com/rui314/chibicc/commit/aaf10459d93fb6c0f4539cb792c02a8d15cb0299).
Earlier explanations are available in Git history.

## What changed

Integer tokens now carry their type. U requests unsigned, L/LL request an
eight-byte integer, and their supported combinations work in either order.
Decimal unsuffixed numbers choose int or long. Nondecimal numbers may also
choose unsigned int or unsigned long to fit their bit pattern. Character literals
carry int type. Parser-created numeric nodes still default to int.

Python parses the magnitude, selects the historical type, then stores the signed
64-bit representation in Token.value. Thus hex ffffffffffffffff is unsigned long
with value -1 internally. The original also accepts the maximum unsigned value
in decimal as signed long; its right shift is arithmetic. Hex/binary prefixes now
require an actual base-valid digit, changing malformed-prefix diagnostic positions.

The port accepts magnitudes through 2**64-1. Larger values get an explicit error;
upstream strtoul can saturate on overflow because this commit ignores errno.
Python uses exact integer conversion rather than host C library conversion.

## Assembly and WSL example

```sh
printf 'int main(void){return -1ULL>>62;}\n' > /tmp/lesson132.c
python3 python/main.py /tmp/lesson132.c > /tmp/lesson132.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson132 /tmp/lesson132.s
/tmp/lesson132
echo $?
```

The unsigned-long operand uses all 64 bits and `shr %cl,%rax`; shifting leaves
3, the exit status. Tests check suffix types and spelling, inferred unsigned
hex types, decimal/hex maximum-value behavior, malformed suffixes, range errors,
assembly widths, execution, and the expanded original literal program.

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
