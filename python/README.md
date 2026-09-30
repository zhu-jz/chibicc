# Lesson 32: Global variables

Original chibicc commit: [`a4d3223a7215712b86076fad8aaf179d8f768b14`](https://github.com/rui314/chibicc/commit/a4d3223a7215712b86076fad8aaf179d8f768b14).
Earlier explanations are available in Git history.

## What changed

Top-level declarations can now create int/pointer/array globals. Lookahead
parses a declarator to distinguish a function type from a variable type.
Variable lookup checks function locals first, then existing global objects.
Global initializers and forward variable references are not supported yet.

The generator emits globals first in `.data`, with `.globl`, a symbol label,
and `.zero size`. This reserves zero-filled storage. Global address calculation
uses `lea x(%rip),%rax`, while locals use frame-relative offsets. Existing
load/store and array logic works for either address. Functions are emitted
in `.text` as before.

## Run it

```sh
python3 python/main.py 'int x; int main(){x=3; return x;}' > /tmp/lesson32.s
cat /tmp/lesson32.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson32 /tmp/lesson32.s
/tmp/lesson32
echo $?
```

The executable prints nothing; the last command shows **3**. Use an interactive
shell without `set -e` for nonzero statuses. The body calculates x's global
address, stores 3 there, and loads it again for the return value. An untouched
global returns zero, unlike an uninitialized stack local.

Tests cover all upstream globals and array positions, sizes, zero initialization,
updates across functions, local shadowing, data directives, address instructions,
and unsupported initializers/forward references. Function headers now need a
function declarator to select the function branch. Python lists replace global
linked lists; no new intentional Python/C behavior is introduced.

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
