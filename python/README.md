# Lesson 120: Static local variables

Original chibicc commit: [`319772b42ebc2311a56ef54e1e9a60c5583971b1`](https://github.com/rui314/chibicc/commit/319772b42ebc2311a56ef54e1e9a60c5583971b1).
Earlier explanations are available in Git history.

## What changed

A static local becomes an anonymous global object with a unique assembler name.
Its source name is bound only in the current block, while its storage persists
across calls. Constant initializers use .data; omitted initializers use zero-filled
.bss. It consumes no local stack slot and emits no initializer statement at runtime.

Python reuses unique-name generation, scope bindings, and global serialization.
The original commit does not apply local _Alignas overrides in this static path.
Static initialization remains compile-time only; a function call is rejected.
The anonymous symbol convention provides distinct storage for same-named locals.

## Assembly and WSL example

```sh
printf 'int f(void){static int x=40;return ++x;}int main(){f();return f();}\n' > /tmp/lesson120.c
python3 python/main.py /tmp/lesson120.c > /tmp/lesson120.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson120 /tmp/lesson120.s
/tmp/lesson120
echo $?
```

Assembly stores the initial 40 once in anonymous .data storage. Each call loads
and increments that same object via RIP-relative addressing. The second call
returns 42. Tests verify persistence, zero initialization, distinct function-local
objects, static arrays, absence of stack initialization, nonconstant rejection,
actual execution, and the updated original function program.

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
