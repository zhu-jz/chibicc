# Lesson 250: Include optional tokens in variadic macros

Original chibicc commit: [`338144869fa82097d7767a032cbaac616ba0cd01`](https://github.com/rui314/chibicc/commit/338144869fa82097d7767a032cbaac616ba0cd01).
Earlier explanations are available in Git history.

During function-like macro substitution, `__VA_OPT__(tokens)` now keeps its
parenthesized tokens only when the raw `__VA_ARGS__` token list is nonempty.
Balanced parentheses allow nested expressions and commas inside that token list.
This lets a variadic macro insert a separator only when extra arguments exist.

```sh
printf '#define SUM(x,...) x __VA_OPT__(+) __VA_ARGS__\nint main(void){return SUM(12,30);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Preprocessing produces `12+30`. Assembly loads the operands, adds them and
returns 42. Tests check empty and nonempty arguments, nested parentheses, optional
separators and the original sprintf fixtures. Python copies tokens into a list
where C links them into the output chain.
This historical implementation tests raw emptiness, so an argument macro that
later expands to nothing still counts as present. It copies the optional body
without substituting named parameters inside it; that limitation is preserved
and explicitly tested rather than claiming full modern standard behavior.

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
