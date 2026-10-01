# Lesson 194: Recognize wide character literal prefixes

Original chibicc commit: [`7746e4ee0b254da6311202c7db3d2fddd4c6a52c`](https://github.com/rui314/chibicc/commit/7746e4ee0b254da6311202c7db3d2fddd4c6a52c).
Earlier explanations are available in Git history.

The tokenizer now recognizes `L` immediately followed by a character literal
quote. It passes both the token's starting position and the quote's position
to the existing character reader, preserving the full source spelling.

At this historical step, L-prefixed literals have exactly the same behavior
as ordinary character literals: int type, existing escape decoding, and the
same signed-byte conversion. This adds recognition without introducing later
wide-character types or Unicode decoding. Python uses an optional quote index
instead of the C reader's second pointer.

```sh
printf "int main(void){return L'a';}\n" > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 97, the ASCII value of a
```

Assembly loads the literal's integer value into %rax and returns. sizeof an
L-prefixed literal yields four bytes at this step. Tests cover its type, token
spelling/location, escapes, the preserved signed-byte behavior, diagnostics
and executable results; the upstream literal fixture runs unchanged.

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
