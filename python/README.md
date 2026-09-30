# Lesson 24: Calls with up to six arguments

Original chibicc commit: [`964b1d2a0e3e46882743f16703cb12b51e724179`](https://github.com/rui314/chibicc/commit/964b1d2a0e3e46882743f16703cb12b51e724179).
Earlier explanations are available in Git history.

## What changed

Calls accept comma-separated assignment expressions. FUNCALL keeps arguments
in a Python list, replacing upstream's linked list. For `sub(5,3)`, the
compiler evaluates 5 then 3, pushing each result. It pops them into `%rsi`
and `%rdi`, clears `%rax`, and emits `call sub`.

The six integer/pointer argument registers are `%rdi`, `%rsi`, `%rdx`, `%rcx`,
`%r8`, and `%r9`. Reverse popping maps the first argument to the first register.
Saving values on the stack protects them while later arguments make nested
calls. Binary operators still evaluate their right operand first; call
arguments follow upstream's left-to-right order.

## Run it

```sh
printf 'int sub(int x,int y) { return x-y; }\n' > /tmp/helper24.c
python3 python/main.py '{return sub(5,3);}' > /tmp/lesson24.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson24 /tmp/lesson24.s /tmp/helper24.c
/tmp/lesson24
echo $?
```

The last command shows **2**. The executable itself prints nothing. Use an
interactive shell without `set -e` for nonzero statuses. GCC compiles the
helper, then assembles and links our output.

Tests include all five new upstream examples, deeply nested six-argument
calls, noncommutative subtraction, assignment side effects, register order,
and malformed separators. The port deliberately reports a compile error
above six arguments; upstream would index beyond its register array. Calls
still lack temporary-stack alignment adjustment at this original stage.
Local slots remain eight bytes; numeric tokens retain the checked 32-bit range.

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
