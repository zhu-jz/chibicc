# Lesson 25: Function definitions without parameters

Original chibicc commit: [`6cb4220f339e7d2a894e44b61c90c576a482914b`](https://github.com/rui314/chibicc/commit/6cb4220f339e7d2a894e44b61c90c576a482914b).
Earlier explanations are available in Git history.

## What changed

Input is now a sequence of function definitions, rather than one bare block:

```c
int main() { return ret32(); }
int ret32() { return 32; }
```

The parser returns a list of Function objects, each with its name, body, and
locals. A function type records its return type. Every function resets its
local-variable list, so names and offsets belong to that function alone.
Definitions have no parameters in this lesson, although calls can pass up to
six arguments to external functions.

The generator emits a `.globl` declaration and stack frame per function.
Returns jump to `.L.return.main` or `.L.return.ret32`, so cleanup labels do
not collide. Control-flow labels remain unique throughout the compilation.
`call ret32` can refer to a later definition; the assembler/linker resolves it.
An empty translation unit emits no assembly. Trailing tokens are now parsed
as further definitions, rather than silently ignored after the first block.

## Run it

```sh
python3 python/main.py 'int main(){return ret32();} int ret32(){return 32;}' > /tmp/lesson25.s
cat /tmp/lesson25.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson25 /tmp/lesson25.s
/tmp/lesson25
echo $?
```

The executable prints nothing; the last command displays **32**. Use an
interactive shell without `set -e` for nonzero statuses. GCC assembles and
links the emitted code with the C runtime.

Tests migrate earlier fixtures to `int main(){...}`, check multiple functions,
independent locals, forward calls, distinct cleanup labels, empty input,
invalid headers, and rejection of the former bare-block input. As upstream,
this small parser does not yet check that the declarator's type is a function,
so a header without parentheses can also parse. Python uses a function list
instead of C's linked list and retains a separate declaration-name type copy.
All slots remain eight bytes; call alignment limitations are unchanged.

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
