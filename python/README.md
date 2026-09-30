# Lesson 26: Function parameters

Original chibicc commit: [`aacc0cfec24e0aef1e884ac8b657e182a33a7b1c`](https://github.com/rui314/chibicc/commit/aacc0cfec24e0aef1e884ac8b657e182a33a7b1c).
Earlier explanations are available in Git history.

## What changed

Definitions now accept named int/pointer parameters:

```c
int main(){return sub2(4,3);}
int sub2(int x,int y){return x-y;}
```

Function types keep parameter types in source order. The parser creates local
objects for them before parsing the body. Function.params keeps those objects
in argument order; Function.locals also includes later body declarations.
A shallow type copy preserves each parameter name without copying pointer bases.
Type annotation now visits call arguments too, rejecting invalid dereferences
inside them.

The prologue saves argument registers into their assigned stack slots. For
sub2 without other locals this is `mov %rdi, -8(%rbp)` followed by
`mov %rsi, -16(%rbp)`. Parameter reads and assignments then reuse ordinary
local-variable code. Each recursive call gets a separate stack frame.

## Run it

```sh
python3 python/main.py 'int main(){return sub2(4,3);} int sub2(int x,int y){return x-y;}' > /tmp/lesson26.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson26 /tmp/lesson26.s
/tmp/lesson26
echo $?
```

The executable prints nothing; the last command shows **1**. Use an interactive
shell without `set -e` for nonzero statuses. Tests cover upstream add/sub/fib,
all six register positions, pointer parameters, local offsets, and argument
annotation. Python replaces upstream's recursive list construction with lists
in source order. It reports unsupported parameter counts above six instead
of indexing outside a C register array. Signature compatibility, prototypes,
block scopes, and temporary-stack call alignment remain unsupported at this stage.
All local slots are still eight bytes.

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
