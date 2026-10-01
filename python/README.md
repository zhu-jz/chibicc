# Lesson 235: Recognize C11 Unicode identifiers

Original chibicc commit: [`0e5d250ebfd29845c8c26b0ad63379994a2b8560`](https://github.com/rui314/chibicc/commit/0e5d250ebfd29845c8c26b0ad63379994a2b8560).
Earlier explanations are available in Git history.

Identifiers now use the original C11 code-point ranges for starting and
continuing characters. Greek, Japanese and many other characters are allowed;
combining marks can continue a name but cannot start it. These rules differ
from Python's isidentifier, so unicode.py preserves the original range tables
and the archive build includes that module.

```sh
cat > /tmp/lesson.c <<'C'
int π=42;int main(void){return π;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The assembler retains the UTF-8 global symbol π. Main takes its address and
loads the stored integer. Tests run Unicode locals and globals, a combining
mark, macro names, universal-escape spelling, allowed ranges and a rejected
symbol, plus original fixtures and the packaged compiler. Python already walks
decoded characters, replacing C's byte-length decode_utf8 scan. It performs no
identifier normalization. Its previously documented Unicode whitespace handling
is retained, including characters C's byte-oriented whitespace scan differs on.

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
