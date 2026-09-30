# Lesson 89: Goto and labeled statements

Original chibicc commit: [`6116cae4c4b98ef9ed55736f3a6c1d872de97767`](https://github.com/rui314/chibicc/commit/6116cae4c4b98ef9ed55736f3a6c1d872de97767).
Earlier explanations are available in Git history.

## What changed

`goto name;` and `name: statement` get GOTO/LABEL nodes. Parsing records them,
then resolves jumps after the whole function is known, allowing forward labels.
Each label receives a unique assembly name from the parser's counter. Labels
have function scope, independent of variable names and ordinary block scope.
An unresolved jump reports `use of undeclared label` at the identifier.

Python lists replace the original goto_next linked lists; goto entries also
retain the label token for the diagnostic. The lists reset after each function.
Duplicate-label validation remains incomplete in this historical implementation.

## Assembly and WSL example

```sh
printf 'int main(){goto answer;return 1;answer:return 42;}\n' > /tmp/lesson89.c
python3 python/main.py /tmp/lesson89.c > /tmp/lesson89.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson89 /tmp/lesson89.s
/tmp/lesson89
echo $?
```

`jmp .L..N` transfers control directly to the matching `.L..N:` label, skipping
the first return. Main exits with 42. Tests cover forward/backward jumps, labels
inside blocks, repeated label spellings across functions, variable/label name
coexistence, unresolved diagnostics, matched assembly symbols, and updated
original control programs.

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
