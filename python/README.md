# Lesson 180: Add the defined operator

Original chibicc commit: [`5cb2f89e6a49cac8ddb16f46df92c31fa2507b9a`](https://github.com/rui314/chibicc/commit/5cb2f89e6a49cac8ddb16f46df92c31fa2507b9a).
Earlier explanations are available in Git history.

Conditional expressions now recognize `defined NAME` and `defined(NAME)`.
The operand must be an identifier. It becomes a numeric token containing 1
when the macro exists and 0 otherwise, before the rest of the expression is
macro-expanded. The operand's replacement body is never expanded for this test.

The rewrite uses the existing tokenizer to create an ordinary integer token
with its C type and synthetic source information. Arithmetic and logical
operators then work through the usual constant-expression parser. This
operator applies only in `#if` and `#elif` expressions; `#ifdef` remains a direct
name lookup. Unknown ordinary identifiers still produce an error at this step.

```sh
printf '#define PRESENT\n#if defined(PRESENT) && !defined(ABSENT)\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The condition becomes `1 && !0` and selects the function. Assembly loads 42 into
`%rax` and returns, with no runtime definition checks. Tests cover both syntaxes,
logical/arithmetic combinations, function-like and undefined names, undefinition,
unexpanded operands and malformed syntax.

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
