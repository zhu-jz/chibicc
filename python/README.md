# Lesson 84: Binary bitwise operators

Original chibicc commit: [`86440068b43d6f9c93fdb07c1c2279cbab579e73`](https://github.com/rui314/chibicc/commit/86440068b43d6f9c93fdb07c1c2279cbab579e73).
Earlier explanations are available in Git history.

## What changed

Binary &, ^, and | operate on individual bits. New parser levels establish C's
precedence: equality binds tighter than &, then ^, then |, then assignment.
Unary & remains address-of. &=, ^=, and |= reuse the one-address-evaluation
compound-assignment helper. Operand types undergo usual arithmetic conversion.

The original emitter always uses rdi/rax for these bitwise instructions, even
when the expression type is int; this Python port matches it. Both operands are
evaluated, unlike short-circuit operators. No Python expression evaluator is used.

## Assembly and WSL example

```sh
printf 'int main(){int x=15;x^=5;return x;}\n' > /tmp/lesson84.c
python3 python/main.py /tmp/lesson84.c > /tmp/lesson84.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson84 /tmp/lesson84.s
/tmp/lesson84
echo $?
```

`xor %rdi, %rax` turns binary 1111 xor 0101 into 1010, decimal 10; the assignment
stores that result. Main exits with 10. Tests cover operators, compound forms,
precedence, address-of coexistence, wide values, emitted instructions, real
execution, and updated upstream fixtures.

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
