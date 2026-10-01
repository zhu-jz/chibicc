# Lesson 134: Unsigned pointer comparisons

Original chibicc commit: [`6880a39d2a5aec8e5ed32c276109936ed503d0bb`](https://github.com/rui314/chibicc/commit/6880a39d2a5aec8e5ed32c276109936ed503d0bb).
Earlier explanations are available in Git history.

## What changed

pointer_to now marks pointer types unsigned. Existing common-type conversion
preserves that flag, so relational pointer comparisons use unsigned setb/setbe.
An address with its top bit set no longer compares as a negative signed long.
Pointer subtraction still has the explicit signed-long result from lesson 133.

Python sets the same single field as upstream. Tests use cast integer addresses
to check the historical compiler behavior without dereferencing them.

## Assembly and WSL example

```sh
printf 'int main(void){return (void*)0xffffffffffffffff>(void*)0;}\n' > /tmp/lesson134.c
python3 python/main.py /tmp/lesson134.c > /tmp/lesson134.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson134 /tmp/lesson134.s
/tmp/lesson134
echo $?
```

The parser represents > by reversing operands for <. Code generation compares
all 64 bits and uses setb, giving exit status 1. Tests check both relational forms,
the pointer type flag, signed differences, emitted comparison, execution, and
the updated original arithmetic program.

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
