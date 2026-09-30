# Lesson 68: Implicit arithmetic conversions

Original chibicc commit: [`8b430a6c5fd6d33a637f2c615f8e5ec59e7be30e`](https://github.com/rui314/chibicc/commit/8b430a6c5fd6d33a637f2c615f8e5ec59e7be30e).
Earlier explanations are available in Git history.

## What changed

Type annotation now inserts CAST nodes. Char and short arithmetic promotes
to int; an eight-byte operand selects long; a pointer left operand selects a
pointer to its base. Both binary operands convert to that common type.
Comparisons return int. Unary minus also promotes its operand, and assignment
converts its right operand to the left type (struct copying remains separate).

A numeric node now selects int if its value fits signed thirty-two bits,
otherwise long. Pointer scaling constants are explicitly long so multiplying
a negative int index first sign-extends it to the address width. Char/short
loads extend to eax, and a later cast to long extends eax to rax as needed.
Functions still default to long call results; full call and return conversion
rules remain incomplete at this original stage.

Python keeps the cast-building helper in type.py to avoid an import cycle
between the parser and type annotator; C exports it from parse.c through its
header. Grammar tests ignore only implicit wrappers (which share the operand's
source token). New conversion tests inspect actual wrappers and their types,
while explicit casts stay visible in grammar comparisons.

## Assembly and WSL example

```sh
printf 'int main(){char x=-1;long y=x;return y<0;}\n' > /tmp/lesson68.c
python3 python/main.py -o /tmp/lesson68.s /tmp/lesson68.c
cat /tmp/lesson68.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson68 /tmp/lesson68.s
/tmp/lesson68
echo $?
```

`movsbl (%rax), %eax` loads x's signed byte; `movsxd %eax, %rax` widens it
before storing into the long y. The signed comparison returns 1, displayed by
the shell. Small-literal arithmetic now uses eax/edi and can wrap at thirty-two
bits; overflow tests describe emitted machine behavior, not portable C rules.
Tests cover mixed signed arithmetic, promotions and sizeof, assignment casts,
negative variable indices, wrapper metadata, and all updated upstream fixtures.
The full Python suite is run to check instruction and runtime progression.

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
