# Lesson 177: Add macro stringizing

Original chibicc commit: [`8f6f7925a04ca070167a38b8952a1a0bb7b63d23`](https://github.com/rui314/chibicc/commit/8f6f7925a04ca070167a38b8952a1a0bb7b63d23).
Earlier explanations are available in Git history.

In a function-like replacement body, `#` followed by a parameter converts its
actual argument tokens to a string literal. Unlike ordinary substitution, it
uses the unexpanded argument: a macro name becomes its spelling rather than
its replacement. Leading and trailing spaces disappear and internal recorded
spaces collapse to one. Quotes and backslashes are escaped for C literal text.

The generated quoted text is passed through the existing tokenizer, giving it
the usual decoded bytes and array type. A small synthetic File preserves the
template's filename and file number without adding a real input file, matching
the C approach. Python string operations replace manual buffer sizing/copying.
A `#` followed by anything other than a parameter is diagnosed.

```sh
printf '#define STR(x) #x\nint main(void){return STR(abc)[2];}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 99, the ASCII value of c
```

Assembly stores the string bytes in global data, computes the address of its
third byte, loads that character, and returns its value in `%rax`. Tests check
spacing, unexpanded names, escaping, empty strings, array size, diagnostics and
an executable character load. The original stringizing fixture runs unchanged.

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
