# Lesson 96: Compile-time constant expressions

Original chibicc commit: [`79f5de21eb706ea5486fd682a83ffbde7e4d16a9`](https://github.com/rui314/chibicc/commit/79f5de21eb706ea5486fd682a83ffbde7e4d16a9).
Earlier explanations are available in Git history.

## What changed

Array bounds, enumerator initializers, and case labels now parse conditional
expressions and evaluate their typed syntax trees at compile time. Arithmetic,
comparisons, bitwise operations, shifts, casts, comma, and conditional/logical
operators are supported. Short-circuit branches skip unused nodes, and comma
evaluates only its right operand. Variables and function calls in evaluated
positions report `not a compile-time constant`.

Python's explicit evaluate_constant function walks Nodes; it never calls Python
eval. C's helper lives in parse.c; Python keeps it in constexpr.py. Division and
remainder use integer-only truncation toward zero, avoiding Python's different
negative // and % behavior. Int-sized destination fields narrow to signed 32 bits.

This historical evaluator masks casts to 8/16/32 bits as unsigned values, even
for signed char or _Bool, so its behavior can differ from runtime casts. It also
computes intermediate arithmetic at host integer width rather than always using
the expression's runtime width. Python intermediates are unbounded; overflowing
C int64 intermediates have no portable match. Constant division by zero and
invalid shift counts produce Python diagnostics instead of host faults or UB.

## Assembly and WSL example

```sh
printf 'enum{N=3*2};int main(){char a[N+1];return sizeof(a);}\n' > /tmp/lesson96.c
python3 python/main.py /tmp/lesson96.c > /tmp/lesson96.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson96 /tmp/lesson96.s
/tmp/lesson96
echo $?
```

The compiler computes N=6 and the array length 7 before allocating stack space.
sizeof becomes `mov $7, %rax`; no runtime multiplication is emitted for the bound.
The shell displays 7. Tests cover all expression categories through the original
constexpr fixture, negative/large exact division, enum/case expressions, discarded
branches, historical cast behavior, narrowed bounds, diagnostic errors, assembly,
and real executables.

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
