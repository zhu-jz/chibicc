# Lesson 139: Floating-point literals

Original chibicc commit: [`1e57f72d8adf15937856a3ca3ca0e16ccb37421e`](https://github.com/rui314/chibicc/commit/1e57f72d8adf15937856a3ca3ca0e16ccb37421e).
Earlier explanations are available in Git history.

## What changed

Numeric tokens and nodes now carry fvalue alongside integer value. Decimal
fractions/exponents and hexadecimal fractions can form floating constants; f/F
chooses four-byte float, while no suffix or l/L chooses eight-byte double.
The emitter places the IEEE bit pattern in an integer register and moves it into
xmm0. sizeof can inspect these literal types.

Python uses float/float.fromhex and struct.pack with explicit little-endian
encoding, replacing C strtod and union bit reinterpretation. Float32 overflow
becomes infinity like a target float conversion. Integer overflow remains a port
diagnostic. As upstream, integer trial parsing no longer rejects leftover letters;
malformed integer spellings are rejected later by the parser.

This step adds constants only. Floating type keywords, arithmetic, conversions,
variables and floating function signatures are not yet fully implemented. The
historical scanner recognizes hex floats when a fraction triggers float parsing;
hex exponent-only spellings are not added ahead of the original history.

## Assembly and WSL example

```sh
printf 'int main(void){1.5f;return sizeof(1.5f);}\n' > /tmp/lesson139.c
python3 python/main.py /tmp/lesson139.c > /tmp/lesson139.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson139 /tmp/lesson139.s
/tmp/lesson139
echo $?
```

The literal emits `mov $1069547520,%eax` followed by `movq %rax,%xmm0`, encoding
float32 1.5. Main's integer return is sizeof(float), so exit status is 4. Tests
inspect actual xmm0 bits with a small assembly helper, check decimal/hex spellings,
suffix types, exact instructions, sizeof, malformed integers, execution, and the
updated original literal program.

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
