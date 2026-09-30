# Lesson 51: Aligned local stack slots

Original chibicc commit: [`dfec1157b41bb86c8cb66eee0b0cbdb9dcccb6f4`](https://github.com/rui314/chibicc/commit/dfec1157b41bb86c8cb66eee0b0cbdb9dcccb6f4).
Earlier explanations are available in Git history.

## What changed

Stack allocation now respects each local variable's alignment. Walking the
function's locals in their existing reverse declaration order, first add the
variable's size, round the running offset up to its alignment, then negate
that offset to get its address relative to `%rbp`. The complete frame is
still rounded to 16 bytes. Struct fields already have internal alignment;
this commit also aligns their containing local object.

For `int x; char y;`, allocation visits y first: y is at -1 and x at -16.
The seven-byte gap makes x's start divisible by eight. For `char x; int y;`,
y is at -8 and x at -9, with no intervening padding. No extra instruction
executes to create padding; only addresses and frame size change.

Python reuses align_to with integer `//`. Global data alignment and call-site
temporary-stack alignment remain at their previous stage; this commit only
changes local-variable offsets. Ints are still eight bytes. Upstream's new
address-difference examples intentionally depend on this compiler's layout
rather than portable C guarantees about separate local variables.

## Assembly and WSL example

```sh
printf 'int main(){int x=42;char y=1;return x;}\n' > /tmp/lesson51.c
python3 python/main.py -o /tmp/lesson51.s /tmp/lesson51.c
cat /tmp/lesson51.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson51 /tmp/lesson51.s
/tmp/lesson51
echo $?
```

The prologue reserves 16 bytes. Addresses use `lea -1(%rbp), %rax` for y and
`lea -16(%rbp), %rax` for x. The typed stores and loads are unchanged, and
the shell displays status 42. Tests inspect offsets and frame sizes for both
orders and a struct/char mixture, run the two upstream address-difference
examples, and run the updated C variable fixture with the other C fixtures.

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
