# Lesson 225: Decode wide character literals as code points

Original chibicc commit: [`a57c661d46d9523bed01ad1b074f7a78d9e94ca3`](https://github.com/rui314/chibicc/commit/a57c661d46d9523bed01ad1b074f7a78d9e94ca3).
Earlier explanations are available in Git history.

Character decoding now reads a Unicode code point. L-prefixed literals keep
the signed 32-bit value; ordinary character literals truncate it to a signed
byte afterward. Escape decoding retains its integer value until that choice
is made, so a wide hexadecimal escape can represent more than one byte.
String numeric escapes continue to store only their low byte.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return L'β'-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Beta's code point is 946; the assembly loads that immediate and subtracts
904. Tests cover Greek, Japanese, emoji, large hexadecimal escapes, four-byte
literal types, ordinary signed-byte truncation, universal escapes and original
fixtures. Python source is already decoded as strict UTF-8, so ord replaces
manual decode_utf8. It rejects malformed UTF-8 during input decoding; diagnostic
positions count characters. L'\xff' is now positive 255, intentionally advancing
beyond the earlier placeholder L-prefix behavior.

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
