# Lesson 175: Allow parenthesized macro arguments

Original chibicc commit: [`c7d7ce0f0cbd5869259a3365211ab92126a27ff6`](https://github.com/rui314/chibicc/commit/c7d7ce0f0cbd5869259a3365211ab92126a27ff6).
Earlier explanations are available in Git history.

The macro argument reader now keeps a parenthesis depth. It stops at a comma
or closing parenthesis only at depth zero. Parenthesized arithmetic, comma
expressions and nested function or macro calls remain complete argument lists.

This is a small change to token collection, not to parsing or evaluation.
Only parentheses affect this depth, matching the original C implementation.
End of input inside an incomplete argument still produces a diagnostic.

```sh
printf '#define PRODUCT(x,y) x*y\nint main(void){return PRODUCT((2+3),4);}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 20
```

Expansion yields `(2+3)*4`. Assembly adds 2 and 3, multiplies by 4, and returns
20 in `%rax`. Tests cover nested parentheses, comma expressions, function calls
with their own arguments, nested macro invocations and incomplete input. The
previous lesson's nested-argument limitation test is updated for this change.

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
