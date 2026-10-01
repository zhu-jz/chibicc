# Lesson 230: Transcode U-prefixed strings to UTF-32

Original chibicc commit: [`c467ee665de0c385170850ecc895add04b52b8a3`](https://github.com/rui314/chibicc/commit/c467ee665de0c385170850ecc895add04b52b8a3).
Earlier explanations are available in Git history.

U-prefixed strings now use one little-endian four-byte unit per code point,
plus a four-byte zero terminator. Their type is an unsigned-int array. Numeric
escapes keep their low 32 bits; indexed access scales by four and follows
unsigned integer rules. Source spelling remains available for stringizing.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return U"🍣"[0]-127801;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The data section stores code point 127843 as four bytes. Main loads that unit
and subtracts 127801 to return 42. Tests inspect empty/ASCII/Japanese/emoji
bytes and sizes, indexed terminators, unsigned escape shifts, stringizing and
original memcmp fixtures. Python serializes ord values explicitly in little
endian instead of writing through uint32_t pointers. As in the preceding
step, array initialization and concatenation have not yet gained full handling
for wider element sizes.

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
