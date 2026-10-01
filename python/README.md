# Lesson 272: Compute variable-length array sizes at runtime

Original chibicc commit: [`e8667afd08ecbf7c9b05beb4ff399959d9722ff9`](https://github.com/rui314/chibicc/commit/e8667afd08ecbf7c9b05beb4ff399959d9722ff9).
Earlier explanations are available in Git history.

Nonconstant array bounds now create VLA types containing a length expression and
an object holding their computed byte size. Local declarations compute sizes
from the innermost dimension outward, save them once and allocate storage with
the previous alloca machinery. A pointer to a VLA computes the pointed-to size
without allocating that array. sizeof uses the saved size rather than re-reading
a bound variable that may have changed.

```sh
printf 'int main(void){int n=5;int x[n];n=9;return sizeof(x)+22;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly multiplies 5 by the four-byte int element size, saves 20, allocates the
array and later loads that saved 20 for sizeof. Adding 22 returns 42 even after
n becomes 9. Tests cover multidimensional sizes, mixed fixed/runtime dimensions,
pointers to VLAs, single evaluation and rejected initialization, plus original vla.c.
Python omits no-op sizing statements for ordinary declarations, while C emits
NULL_EXPR nodes. VLA types still have an eight-byte local pointer representation.
This step implements sizeof support; dynamic indexing is not extended ahead.
The original constant-expression classifier omits remainder and tests only the
right operand of comma expressions; those historical rules remain. If a fresh
VLA type has no computed size, Python reports an error instead of C's null access.

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
