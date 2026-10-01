# Lesson 145: Definitions with floating parameters

Original chibicc commit: [`c6b30568b407e7b60b6fc2929801669434e4f91a`](https://github.com/rui314/chibicc/commit/c6b30568b407e7b60b6fc2929801669434e4f91a).
Earlier explanations are available in Git history.

## What changed

Function prologues classify each parameter independently as integer/pointer or
floating. movss saves four-byte float parameters and movsd saves eight-byte double
parameters from xmm registers into their local stack slots. Integer parameters
continue to use the six general-purpose argument registers. Returning a floating
expression leaves its result in xmm0 through the normal epilogue.

Python uses two counters in a simple loop instead of traversing a linked list.
Its explicit register-limit errors avoid an out-of-bounds register lookup in the
original implementation. Variadic register-save bookkeeping remains at the
historical implementation for this commit; this step concerns fixed parameters.

## Assembly and WSL example

```sh
printf 'double add(double x,float y){return x+y;}int main(void){return add(20.5,21.5);}\n' > /tmp/lesson145.c
python3 python/main.py /tmp/lesson145.c > /tmp/lesson145.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson145 /tmp/lesson145.s
/tmp/lesson145
echo $?
```

add saves xmm0 with movsd and xmm1 with movss. Its body loads both values,
converts y to double, and adds them. Main converts the returned 42.0 to int, and
the shell displays exit status 42. Tests cover both widths, mixed parameters,
eight floating registers, recursion, calls from GCC-generated code, prologue
instructions, real execution, and the original function examples.

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
