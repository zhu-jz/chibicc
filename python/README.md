# Lesson 236: Accept dollar signs in GNU identifiers

Original chibicc commit: [`adb8b988897758d0d4f74dcd9129bff0831634ae`](https://github.com/rui314/chibicc/commit/adb8b988897758d0d4f74dcd9129bff0831634ae).
Earlier explanations are available in Git history.

The identifier ranges now accept $ as both a first and subsequent character,
following the original GNU extension. Names such as $$$, a$b and $0 become
single IDENT tokens. They work in local declarations and macro names through
the existing parser and preprocessor paths.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){int $$$=42;return $$$;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Local names disappear into frame offsets in assembly; main loads that slot
and returns 42. Tests check raw spellings, local and macro names, trailing-dollar
global/function symbols and original fixtures. Python adds the same dollar
range to both tables, rather than relying on Python identifier rules. This
commit changes accepted token characters only; symbol printing keeps the
original assembler syntax, including its limitations for leading-dollar
external symbols.

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
