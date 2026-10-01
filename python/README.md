# Lesson 144: Calls with floating arguments and results

Original chibicc commit: [`8ec1ebf176b88522fc4ec3980d20c78e13fdd526`](https://github.com/rui314/chibicc/commit/8ec1ebf176b88522fc4ec3980d20c78e13fdd526).
Earlier explanations are available in Git history.

## What changed

Function calls now pass floating arguments through xmm0–xmm7, independently of
the six integer/pointer argument registers. The compiler evaluates arguments
from right to left, saves each result on the stack, then restores them in source
order into their appropriate registers. A floating return already arrives in
xmm0, ready for subsequent arithmetic or conversion.

Python reverses a list instead of recursively visiting a C linked list. This
commit changes the chosen argument evaluation order; C itself does not promise
an order. Calls beyond six integer or eight floating register arguments receive
clear Python errors; passing excess arguments on the stack is not implemented
at this historical point. Definitions with floating parameters are still
incomplete. The original commit also removes the old eax=0 before calls, leaving
floating variadic-call bookkeeping incomplete for now.

## Assembly and WSL example

```sh
printf 'double twice(double);int main(void){return twice(21.0);}\n' > /tmp/lesson144.c
printf 'double twice(double x){return x*2;}\n' > /tmp/lesson144-helper.c
python3 python/main.py /tmp/lesson144.c > /tmp/lesson144.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson144 /tmp/lesson144.s /tmp/lesson144-helper.c
/tmp/lesson144
echo $?
```

The caller restores 21.0 into xmm0 and calls the separately compiled helper. The
helper returns 42.0 in xmm0; cvttsd2sil converts main's result to int, so the shell
shows exit status 42. Tests cover float and double calls, mixed register classes,
nested calls, evaluation order, emitted register restores, and original fixtures.

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
