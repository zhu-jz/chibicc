# Lesson 100: String literal array initializers

Original chibicc commit: [`0d717373cc9e247fc6f6a0e02b0bbd424f0d70b0`](https://github.com/rui314/chibicc/commit/0d717373cc9e247fc6f6a0e02b0bbd424f0d70b0).
Earlier explanations are available in Git history.

## What changed

An array initializer may now be a string literal. The parser copies its decoded
bytes into scalar initializer leaves, up to the smaller of the array length and
string length including the terminating zero. Remaining elements stay zero;
short arrays silently truncate the literal in this original implementation.
Nested arrays can use a string for each row. The same assignment lowering emits
local stores, so a local array initializer needs no separate global string object.

Python min replaces C's MIN macro. Byte values are explicitly interpreted as
signed char before becoming NUM nodes, matching x86-64 C's tok->str[i], including
bytes above 127. The original accepts this path for array kinds without complete
base-type validation; deducing an incomplete array length is still unsupported.

## Assembly and WSL example

```sh
printf 'int main(){char a[4]="abc";return a[2];}\n' > /tmp/lesson100.c
python3 python/main.py /tmp/lesson100.c > /tmp/lesson100.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson100 /tmp/lesson100.s
/tmp/lesson100
echo $?
```

After clearing a, the emitter loads 97, 98, 99, and 0 and stores each byte using
al. Returning a[2] exits with 99, displayed by the shell. Tests check the terminator,
zero padding, truncation, nested rows, escape-byte signedness, direct local-store
assembly, real executables, and updated original initializer programs.

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
