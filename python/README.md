# Lesson 278: Emit ELF symbol types and object sizes

Original chibicc commit: [`8d130ab93f65f7ef79839aba87459e4f9507ba39`](https://github.com/rui314/chibicc/commit/8d130ab93f65f7ef79839aba87459e4f9507ba39).
Earlier explanations are available in Git history.

Initialized data now receives .type name,@object and .size name,bytes directives;
functions receive .type name,@function. Alignment moves after selecting the data
or BSS section, so it applies to the section containing the object. Common symbols
keep their alignment in .comm itself. Function sizes and BSS metadata are not added
by this original step.

```sh
printf 'int answer=42;int main(void){return answer;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly labels answer as a four-byte object and main as a function, then loads
answer through its RIP-relative address and returns 42. These directives describe
symbols to the assembler and linker; they do not execute. Tests inspect the emitted
directives and readelf's object symbol table, and retain alignment/runtime checks.
Python assembles string lists where C prints directives, with the same ELF metadata.

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
