# Lesson 127: Calling variadic functions

Original chibicc commit: [`58fc86137c23adc3d98be40117087c645a9d7e4e`](https://github.com/rui314/chibicc/commit/58fc86137c23adc3d98be40117087c645a9d7e4e).
Earlier explanations are available in Git history.

## What changed

The tokenizer recognizes `...` and function parameter parsing records a variadic
flag when an ellipsis ends the list. Calls can now use explicit variadic
prototypes, including printf and sprintf. Fixed arguments retain declared-type
conversions; later integer/pointer arguments use the existing call path.

Python adds a boolean to Type and consumes the ellipsis directly. This step adds
calling support, not va_start/va_arg implementation inside Python-compiled function
bodies. Up to six total integer/pointer arguments are still supported. The emitter
already writes zero to rax before calls, reporting zero floating-point argument
registers for the System V variadic calling convention.

## Assembly and WSL example

```sh
printf 'int sprintf(char *b,char *f,...);int main(){char b[20];sprintf(b,"%%d",42);return b[0];}\n' > /tmp/lesson127.c
python3 python/main.py /tmp/lesson127.c > /tmp/lesson127.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson127 /tmp/lesson127.s
/tmp/lesson127
echo $?
```

Registers carry b, the format pointer, and 42. The emitter sets rax to zero and
calls libc sprintf. Buffer byte '4' has value 52, the exit status. Tests check
variadic type metadata, ellipsis tokenization, malformed declarations, integer
extras with negative char values, libc formatting, emitted ABI setup, execution,
and the original function/helper examples.

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
