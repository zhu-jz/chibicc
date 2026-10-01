# Lesson 173: Add function-like macro parameters

Original chibicc commit: [`b9ad3e43cf7479712972514aa3f2c55a0f650f76`](https://github.com/rui314/chibicc/commit/b9ad3e43cf7479712972514aa3f2c55a0f650f76).
Earlier explanations are available in Git history.

Function-like definitions now accept named parameters. An invocation collects
one token sequence per parameter, expands that sequence, and substitutes it
where the parameter appears in the replacement body. Python lists store
parameter names and a dictionary maps each name to its argument tokens.

Substitution supplies no implicit grouping. `#define PRODUCT(x,y) x*y` with
arguments `3+4` and `4+5` yields `3+4*4+5`, which is 24. Parenthesizing the body
as `(x)*(y)` instead yields 63. Empty argument sequences are accepted.

This original commit does not yet track nested parentheses while collecting
arguments. Commas and closing parentheses stop an argument immediately. Tests
preserve that limitation and the original punctuation-based count diagnostics.
Function-like recursion still lacks a hideset at this step.

```sh
printf '#define SUM(x,y) (x)+(y)\nint main(void){return SUM(7,35);}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Expansion produces arithmetic tokens. Assembly adds the two values and returns
42 in `%rax`; no macro call exists at runtime. Tests check precedence, argument
expansion, empty arguments, malformed definitions, count errors and the current
nested-parenthesis limitation, alongside the upstream macro program.

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
