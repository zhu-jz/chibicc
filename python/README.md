# Lesson 114: Void parameter lists

Original chibicc commit: [`7a1f816783064a12156807fe0a4d760c2e212d4e`](https://github.com/rui314/chibicc/commit/7a1f816783064a12156807fe0a4d760c2e212d4e).
Earlier explanations are available in Git history.

## What changed

A literal `void` immediately followed by the closing parenthesis now represents
an empty function parameter list. `int f(void)` therefore declares a function
with no parameter objects. Normal named parameter parsing handles other lists.

Python returns the function type and next token index, following upstream's
special case. This commit does not add full argument-count checking or equate
an arbitrary typedef of void with this syntactic special case. Existing empty
`()` lists retain their earlier behavior.

## Assembly and WSL example

```sh
printf 'int f(void){return 42;}int main(void){return f();}\n' > /tmp/lesson114.c
python3 python/main.py /tmp/lesson114.c > /tmp/lesson114.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson114 /tmp/lesson114.s
/tmp/lesson114
echo $?
```

Main calls f without setting argument registers. f moves 42 into rax and returns;
main returns the same value, giving exit status 42. Tests check declarations and
definitions, empty parameter types and objects, emitted call, mixed-list rejection,
actual execution, and updated original function examples.

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
