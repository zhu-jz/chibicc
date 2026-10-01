# Lesson 224: Convert universal character escapes to UTF-8

Original chibicc commit: [`c31886aa7a52fd8639e09bbdf8ac8ea854c313f6`](https://github.com/rui314/chibicc/commit/c31886aa7a52fd8639e09bbdf8ac8ea854c313f6).
Earlier explanations are available in Git history.

Source normalization now replaces nonzero four-digit backslash-u and eight-digit
backslash-U sequences with their characters before tokenization. Other escaped
pairs are copied together, so an escaped backslash does not start a universal
escape. Malformed and zero-valued sequences retain the original fallback.
Ordinary string decoding then stores UTF-8 bytes plus a terminator.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return sizeof("\u03B1\u03B2\u03B3")+35;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Each Greek letter occupies two UTF-8 bytes, making sizeof 7 including zero;
adding 35 returns 42. Tests cover Greek, Japanese, a four-byte emoji, escaped
backslashes, unchanged malformed/zero escapes, invalid code points and original
fixtures. Python already stores source as Unicode and uses chr plus the existing
UTF-8 encoder, so no manual unicode.c port is needed. Unlike the C byte encoder,
Python explicitly rejects surrogates and values beyond Unicode's range with a
source diagnostic. Wide character semantics and Unicode identifiers are not
added by this commit.

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
