# Lesson 181: Replace remaining conditional identifiers with zero

Original chibicc commit: [`a8d76ad435891deee9deebbc3a825062fd6cd45a`](https://github.com/rui314/chibicc/commit/a8d76ad435891deee9deebbc3a825062fd6cd45a).
Earlier explanations are available in Git history.

After processing `defined` and expanding macros in a conditional expression,
any remaining identifier becomes an integer token with value zero. This lets
`#if UNKNOWN` select its alternate branch and `#if UNKNOWN == 0` select its
first branch. A self-referential macro's surviving name becomes zero too.

The rewrite applies only to preprocessing constant expressions. Undeclared
identifiers in program code continue to produce diagnostics. Tokens retain C
integer typing through the existing numeric-token helper; Python does not
interpret the expression itself. The earlier unknown-condition error test is
updated to expect the new behavior.

```sh
printf '#if UNKNOWN == 0\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The condition becomes `0 == 0` before parsing the program. Assembly loads 42
into `%rax` and returns, with no runtime identifier checks. Tests cover logical
and arithmetic use, unknown names in alternative branches, recursive macros,
and unchanged errors for undeclared names in actual code.

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
