# Lesson 135: Unsigned and signed constant evaluation

Original chibicc commit: [`7ba6fe8d94af2a232a9da82b815502513f52e465`](https://github.com/rui314/chibicc/commit/7ba6fe8d94af2a232a9da82b815502513f52e465).
Earlier explanations are available in Git history.

## What changed

Constant division, remainder, comparisons, and 64-bit right shifts now honor
unsigned types. Narrow integer casts sign-extend signed targets and zero-extend
unsigned targets: `(char)255` is -1, while `(unsigned char)255` is 255. The same
cast helper is used for numeric constants and global address initializer addends.

Python masks values for explicit uint64 conversions and restores the signed
64-bit representation returned by upstream's evaluator. Integer-only quotient
calculation keeps exact truncation; division by zero and invalid shift counts
still produce the port's deliberate diagnostics. Unbounded signed-overflow
behavior remains a Python difference where upstream C behavior is undefined.

The historical evaluator still treats _Bool through its one-byte cast rather
than normalizing all nonzero values to one; `(_Bool)256` remains zero at compile
time. This commit does not implement broader constant-expression validation.

## Assembly and WSL example

```sh
printf 'unsigned long g=-1UL>>63;int main(void){return g;}\n' > /tmp/lesson135.c
python3 python/main.py /tmp/lesson135.c > /tmp/lesson135.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson135 /tmp/lesson135.s
/tmp/lesson135
echo $?
```

The shift is evaluated during compilation. Data contains byte 1 and seven zeros;
main loads it and exits with 1, with no runtime shift. Tests check signed casts,
unsigned bounds/comparisons/division/shifts, exact global bytes, emitted data,
existing constant diagnostics, execution, and original constexpr examples.

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
