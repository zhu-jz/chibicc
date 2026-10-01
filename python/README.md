# Lesson 153: Common types for function expressions

Original chibicc commit: [`53e81033ce18fd94fcdcde9010b7c9d41f30aa2c`](https://github.com/rui314/chibicc/commit/53e81033ce18fd94fcdcde9010b7c9d41f30aa2c).
Earlier explanations are available in Git history.

## What changed

After its existing pointer rule, the common-type helper now turns a function
operand into a pointer to that function type. Arithmetic conversions used by
conditional expressions and comparisons therefore retain a callable type instead
of losing the function signature when combining a function with zero.

Python adds two explicit branches, matching the original rule order. This is the
historical common-type implementation; its existing first-pointer rule still
takes priority. Cast nodes retain the chosen signature, and function evaluation
already produces an address from the preceding lesson.

## Assembly and WSL example

```sh
printf 'int f(void){return 42;}int main(void){return (1?f:(void*)0)();}\n' > /tmp/lesson153.c
python3 python/main.py /tmp/lesson153.c > /tmp/lesson153.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson153 /tmp/lesson153.s
/tmp/lesson153
echo $?
```

The conditional branch selects f's address in rax, and call *%rax invokes it.
It returns 42, which the shell displays as the exit status. Tests cover conditional
calls, function comparisons, global pointer initialization, the selected tree
type, indirect assembly, execution, and the original usual-conversion example.

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
