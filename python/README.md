# Lesson 280: Add long double with x87 arithmetic

Original chibicc commit: [`e0bf168041ef60687b5d4454a93fc78c4f3acc48`](https://github.com/rui314/chibicc/commit/e0bf168041ef60687b5d4454a93fc78c4f3acc48).
Earlier explanations are available in Git history.

long double is now a distinct 16-byte, 16-byte-aligned type. Its value uses the x87
80-bit floating format in st(0), rather than the SSE xmm0 register used for float
and double. Arithmetic, comparisons, negation and casts use x87 instructions.
Arguments occupy 16 bytes on the stack; functions return their value in st(0).

```sh
printf 'long double f(long double x){return x+2.0L;}int main(void){return f(40.0L);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly loads constants with fldt, places the argument on the stack with fstpt,
adds using faddp, and converts the returned value using fistpl. The integer cast
temporarily selects truncation in the x87 control word, then restores it. Tests
cover arithmetic, conditions, literals beyond double precision and calls in both
directions with GCC-compiled helpers, plus the original C fixtures.

Python uses Fraction for exact decimal/hexadecimal L literals and rounds their
ratios to an 80-bit significand/exponent with ties to even. The six padding bytes
are zero. Ordinary floating literals and constant evaluation still use Python's
double precision. C's initializer evaluator also returns double; this commit does
not add long-double global initialization, so Python reports unsupported size.
The original predefined __SIZEOF_LONG_DOUBLE__ still says 8 despite sizeof being
16. Historical narrow-integer cast instructions and x87 expression-stack limits
are preserved; this step does not introduce later corrections.

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
