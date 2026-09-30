# Lesson 29: Array subscripts

Original chibicc commit: [`648646bba704745274fcd4fef3b7029c7f7e0fcd`](https://github.com/rui314/chibicc/commit/648646bba704745274fcd4fef3b7029c7f7e0fcd).
Earlier explanations are available in Git history.

## What changed

The grammar gains `postfix = primary ("[" expr "]")*`. Unary operators now
use postfix as their operand base, giving subscripting higher precedence.
Each `x[y]` becomes a DEREF node around the existing pointer-addition helper.
Repeated brackets support multidimensional access without a new node kind.

`x[1][2]` first selects a row, then an element. The generated assembly scales
the first offset by the row size and the second by the element size, then
loads or stores through the resulting address. `x[1]` and `*(x+1)` emit exactly
the same instructions. Because addition handles integer + pointer too,
`2[x]` is valid and equivalent to `x[2]`.

## Run it

```sh
python3 python/main.py 'int main(){int x[2][3]; x[1][2]=5; return x[1][2];}' > /tmp/lesson29.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson29 /tmp/lesson29.s
/tmp/lesson29
echo $?
```

The executable prints nothing; the last command shows **5**. Use an interactive
shell without `set -e` for nonzero statuses. Tests include every distinct new
upstream example, reversed subscripts, all row/column positions, assignment
inside an index, exact equivalence with dereference syntax, and missing brackets.
Bounds remain unchecked. No new intentional Python/C differences are introduced.

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
