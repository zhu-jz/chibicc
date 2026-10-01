# Lesson 122: Return without a value

Original chibicc commit: [`30b3e216cd4eca3b8a13cb0a0613f053ac1d4925`](https://github.com/rui314/chibicc/commit/30b3e216cd4eca3b8a13cb0a0613f053ac1d4925).
Earlier explanations are available in Git history.

## What changed

`return;` now creates a RETURN node with no operand. Code generation skips the
expression and jumps to the same shared epilogue used by value-returning paths.
This supports an early exit from a void function without manufacturing a value.

Python None replaces C's null operand pointer. This historical parser does not
yet enforce return-value rules based on the function's declared return type.
A return without a value does not promise any particular value in rax.

## Assembly and WSL example

```sh
printf 'int g;void f(void){g=42;return;g=1;}int main(){f();return g;}\n' > /tmp/lesson122.c
python3 python/main.py /tmp/lesson122.c > /tmp/lesson122.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson122 /tmp/lesson122.s
/tmp/lesson122
echo $?
```

After storing 42, f jumps to .L.return.f and skips the later store. Main reads g
and returns exit status 42. Tests verify early exit, absent AST operand, emitted
jump without a value instruction, real execution, and updated function examples.

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
