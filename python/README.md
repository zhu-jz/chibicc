# Lesson 172: Add zero-argument function-like macros

Original chibicc commit: [`dec3b3fa02ffb343c37f82d36ae02be6bb30eb03`](https://github.com/rui314/chibicc/commit/dec3b3fa02ffb343c37f82d36ae02be6bb30eb03).
Earlier explanations are available in Git history.

A definition whose opening parenthesis immediately follows its name is now
function-like: `#define ANSWER() 42` expands only when followed by `()`.
Without an argument list, its name remains an ordinary identifier. A space or
comment before the definition's parenthesis instead makes it object-like.
This step accepts no macro parameters or arguments.

The tokenizer records whether whitespace or a comment preceded each token.
`-E` now uses that information instead of inserting a space before every token.
Multiple spaces collapse to one, and indentation at line starts is omitted.
Macro replacement tokens still carry their definition's spacing. Function-like
expansion at this original step does not yet add a hideset; recursive function
macros remain a limitation. Object-like recursion protection is retained.

```sh
printf '#define ANSWER() 42\nint main(void){return ANSWER ();}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

After expansion the return expression is a number, so assembly loads 42 into
`%rax` and returns. It makes no function call for the macro. Tests check bare
identifiers, empty bodies, object-like parentheses, whitespace and comments,
`-E` output, rejected parameters and arguments, and executable exit values.

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
