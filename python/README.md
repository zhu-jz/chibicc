# Lesson 238: Skip a leading UTF-8 byte-order marker

Original chibicc commit: [`2b2fa25507cdc491d2b5dafb2c4b5e33158b996a`](https://github.com/rui314/chibicc/commit/2b2fa25507cdc491d2b5dafb2c4b5e33158b996a).
Earlier explanations are available in Git history.

File and stdin normalization now removes one leading UTF-8 BOM before newline
canonicalization, continuation removal and universal-escape conversion. This
also applies to included headers. UTF-8 byte order needs no marker, so the
leading bytes contribute no token or diagnostic column.

```sh
printf '\357\273\277int main(void){return 42;}\r\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The generated assembly is identical to ordinary source: main loads 42 and
returns. Tests check -E stdin output, a real executable, a BOM-marked header,
normalized File contents, first-token position and original fixtures. Python
recognizes the decoded U+FEFF character where C skips three UTF-8 bytes.
Only the leading marker is removed; interior characters and raw tokenize
calls retain their supplied text.

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
