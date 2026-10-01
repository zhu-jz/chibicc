# Lesson 229: Transcode u-prefixed strings to UTF-16

Original chibicc commit: [`9cabe1f204a8a6139e8b072dfd6f0a15275ad25f`](https://github.com/rui314/chibicc/commit/9cabe1f204a8a6139e8b072dfd6f0a15275ad25f).
Earlier explanations are available in Git history.

u-prefixed strings now contain little-endian UTF-16 code units and have an
unsigned-short array type. Supplementary characters become a surrogate pair,
followed by one zero unit. Numeric escapes write one truncated sixteen-bit
unit. Python uses the standard utf-16-le encoder for ordinary characters and
explicit integer bytes for escapes, replacing the C manual surrogate calculation.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return sizeof(u"🍣")+36;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The emoji uses two units plus zero, so its array size is six bytes. Indexed
loads scale by two and use unsigned-short extension. Tests inspect empty,
ASCII, Japanese and emoji payloads, exact surrogate values, escape units,
stringizing, sizeof and original memcmp fixtures. At this historical step,
string-based array initialization still reads individual bytes, and adjacent
string joining still assumes a one-byte terminator. Those paths are not claimed
as complete UTF-16 support; their original changes are still to come.

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
