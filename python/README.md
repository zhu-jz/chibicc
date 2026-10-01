# Lesson 233: Initialize UTF-32 and wide arrays

Original chibicc commit: [`6adba75af879d8ac2bc43a7337b02e64d10e60f1`](https://github.com/rui314/chibicc/commit/6adba75af879d8ac2bc43a7337b02e64d10e60f1).
Earlier explanations are available in Git history.

String initialization now handles four-byte array elements too. It reads
uint32-sized units from the literal payload, then normal assignment or global
serialization converts to the destination's signed or unsigned type. Both
U strings and Linux L wide strings can initialize complete arrays.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){unsigned int x[]=U"β";return x[0]-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Four-byte stores initialize 946 and zero. The indexed load and subtraction
return 42. Tests cover local/global unsigned and signed arrays, supplementary
characters, inferred and truncated bounds, high-bit shifts and original fixtures.
Python extends its existing little-endian unit reader to size 4 rather than
adding pointer casts. Adjacent wide-string concatenation still has its earlier
one-byte assumptions until that original step is reached.

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
