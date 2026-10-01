# Lesson 94: Shift operators

Original chibicc commit: [`d0c0cb74b21f431c62f7eeb8dbc0d6e14c1eff14`](https://github.com/rui314/chibicc/commit/d0c0cb74b21f431c62f7eeb8dbc0d6e14c1eff14).
Earlier explanations are available in Git history.

## What changed

<< and >> parse between addition and relational comparisons. <<= and >>= reuse
compound assignment. The tokenizer matches three-character operators before
two-character ones. The emitter transfers the count from rdi to rcx, because
x86 variable shifts read cl. Left shift uses shl; signed right shift uses sar.
The left operand determines the result type and register width.

The original keeps a char/short left operand's type instead of applying complete
integer promotion. This snapshot preserves that behavior. Python returns the
matched punctuator string rather than C's byte length; int/long shifts execute
as 32/64-bit machine instructions, not as Python's unbounded shifts. Invalid
counts and signed overflow are not diagnosed at this historical stage.

## Assembly and WSL example

```sh
printf 'int main(){int x=21;x<<=1;return x;}\n' > /tmp/lesson94.c
python3 python/main.py /tmp/lesson94.c > /tmp/lesson94.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson94 /tmp/lesson94.s
/tmp/lesson94
echo $?
```

`mov %rdi, %rcx` selects the count, and `shl %cl, %eax` shifts 21 left by one to
make 42. A long left operand uses rax. The shell displays 42. Tests cover signed
right shifts, precedence and associativity, assignments with one address
evaluation, long widths, longest-token matching, type metadata, and updated
original arithmetic programs.

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
