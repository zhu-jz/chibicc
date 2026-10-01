# Lesson 129: Checking function argument counts

Original chibicc commit: [`197689a22b38df2ced90e03117914a2248238c20`](https://github.com/rui314/chibicc/commit/197689a22b38df2ced90e03117914a2248238c20).
Earlier explanations are available in Git history.

## What changed

Calls now reject too few fixed arguments and too many arguments for nonvariadic
functions. Variadic calls require all fixed arguments but allow extras. `f(void)`
has zero fixed arguments and is nonvariadic. Old-style `f()` is represented as
variadic, retaining its unspecified-parameter calling behavior; its definitions
therefore also receive the register-save area introduced in lesson 128.

Python compares list lengths where upstream advances a parameter pointer.
Tests that intend a zero-parameter function now spell `(void)`, keeping their
stack and syntax-tree expectations precise. The original C fixtures retain their
historical source verbatim. The new tests separately check old-style `()` behavior.

## Assembly and WSL example

```sh
printf 'int f(int x){return x;}int main(void){return f(42);}\n' > /tmp/lesson129.c
python3 python/main.py /tmp/lesson129.c > /tmp/lesson129.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson129 /tmp/lesson129.s
/tmp/lesson129
echo $?
```

The valid call passes 42 in edi and exits with 42. Changing it to f() or f(1,2)
now reports an argument-count error before emitting assembly. Tests cover both
errors, void and variadic prototypes, unspecified old-style calls, variadic
save-area flags, zero-argument fixtures, execution, and all original C programs.

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
