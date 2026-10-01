# Lesson 161: Warn about extra include tokens

Original chibicc commit: [`ec149f64d2f5c41a2080c0b4e42e4ef64444b382`](https://github.com/rui314/chibicc/commit/ec149f64d2f5c41a2080c0b4e42e4ef64444b382).
Earlier explanations are available in Git history.

## What changed

The original commit introduces warn_tok and a skip_line helper for tokens after
an include filename. Warnings display the source line and caret but allow
compilation to continue. Python shares a diagnostic formatter between errors
and warnings, preserving the existing filename and line information.

This revision contains an inverted loop: skip_line returns immediately at a
new line, but its loop also tests at_bol when the current token is not at_bol.
Therefore it warns without consuming any extra tokens. Python expresses that
actual behavior directly and records it in tests. Extra text that is valid C
still reaches the parser; arbitrary junk still causes a parse error. The tests
preserve that historical behavior.

## Assembly and WSL example

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson161.h
printf '#include "lesson161.h" int extra;\nint main(void){return answer();}\n' > /tmp/lesson161.c
python3 python/main.py -S -o /tmp/lesson161.s /tmp/lesson161.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson161 /tmp/lesson161.s
/tmp/lesson161
echo $?
```

The compiler warns at int extra, then still emits storage for that global. Main
calls the included answer function and exits with 42. Tests check the warning's
file/line and caret, retained extra declaration, failure for junk, absence of a
warning on a clean include, emitted assembly, execution, and the original fixtures.

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
