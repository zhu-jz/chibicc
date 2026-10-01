# Lesson 228: Read u8-prefixed string literals

Original chibicc commit: [`57b21fe90296c867888d7c8c60d243bc254a39d7`](https://github.com/rui314/chibicc/commit/57b21fe90296c867888d7c8c60d243bc254a39d7).
Earlier explanations are available in Git history.

u8-prefixed strings now use the existing char-array reader. The prefix and
quotes form one STR token; its payload is UTF-8 bytes followed by zero, just
like an ordinary string at this stage. The reader accepts a separate quote
position so diagnostics and stringizing retain the complete source spelling.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){char s[]=u8"α🌮";return sizeof(s)+35;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The two characters occupy six UTF-8 bytes plus zero; the initialized array
has size 7. Its size plus 35 returns 42. Tests inspect the bytes and element
type, initialize a char array, join adjacent strings, preserve the prefix in
stringizing, diagnose an unclosed string and run original fixtures. Python
keeps its existing UTF-8 encoding; this syntax adds no new runtime conversion.
UTF-16, UTF-32 and wide string payloads remain separate later steps.

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
