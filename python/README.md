# Lesson 232: Initialize arrays from UTF-16 strings

Original chibicc commit: [`36230e0827ca33a9b09ea5aa7b06e170fd188ca1`](https://github.com/rui314/chibicc/commit/36230e0827ca33a9b09ea5aa7b06e170fd188ca1).
Earlier explanations are available in Git history.

String-based array initialization now reads complete two-byte units for short
arrays, while char arrays retain signed-byte reading. An omitted array bound
uses the literal's unit count, including zero. Local initialization emits
assignments to each element; global initialization serializes those values.
The original also simplifies its L-character scan increment, which Python
already expressed as a returned next index.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){unsigned short x[]=u"β";return x[0]-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The array contains the complete unit 946 and a zero. Two-byte stores initialize
it, and indexed loading/subtraction returns 42. Tests cover inferred bounds,
local and global arrays, exact serialized bytes, surrogate pairs, truncation
to an explicit shorter bound, zero-filled larger bounds and original fixtures.
Python decodes little-endian slices rather than casting buffer pointers.
Four-byte array initializers remain unsupported at this historical step and
receive CompileError instead of the C unreachable assertion.

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
