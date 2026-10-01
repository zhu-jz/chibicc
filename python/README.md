# Lesson 226: Add u-prefixed character literals

Original chibicc commit: [`454618cd15c2c87d9f5a6a6727e1b09a8e22a799`](https://github.com/rui314/chibicc/commit/454618cd15c2c87d9f5a6a6727e1b09a8e22a799).
Earlier explanations are available in Git history.

u-prefixed character literals now carry an unsigned-short type and the low
sixteen bits of the decoded code point. sizeof(u'a') is 2. The full source
spelling remains one token, so macro stringizing keeps the prefix. Ordinary
and L-prefixed literals retain their respective signed-byte and int behavior.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return u'β'-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The unsigned-short value 946 is promoted for subtraction, leaving 42 in rax.
Tests check ASCII, Greek, Japanese, hexadecimal limits, type size, unsigned
shift, source stringizing and original fixtures. This historical commit calls
the syntax UTF-16, but truncates a supplementary code point rather than emitting
a surrogate pair: u'🍣' is 62307. Python applies the same explicit 0xffff mask;
it does not silently advance to later wide-string or surrogate handling.

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
