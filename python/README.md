# Lesson 28: Arrays of arrays

Original chibicc commit: [`3ce1b2d067164f754dcb4216c193dc98e164b3ce`](https://github.com/rui314/chibicc/commit/3ce1b2d067164f754dcb4216c193dc98e164b3ce).
Earlier explanations are available in Git history.

## What changed

The array suffix recursively parses any following suffix before constructing
its outer array type. Thus `int x[2][3]` is ARRAY(2, ARRAY(3, INT)), not the
reverse. With eight-byte ints it occupies 48 bytes; each row occupies 24.

`x+1` scales its offset by 24 to reach the second row. Dereferencing that
expression produces an array, so the generator keeps its address. Adding
one to that row scales by 8, and the final dereference loads an integer.
No code-generator changes are needed: its array conversion and type-size
arithmetic already support nesting. Subscripting is still unavailable.

## Run it

```sh
python3 python/main.py 'int main(){int x[2][3]; *(*(x+1)+2)=5; return *(*(x+1)+2);}' > /tmp/lesson28.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson28 /tmp/lesson28.s
/tmp/lesson28
echo $?
```

The executable prints nothing; the last command shows **5**. Use an interactive
shell without `set -e` for nonzero statuses. The generated multiplication
nodes compute a 24-byte row offset and an eight-byte element offset before
storing/loading the selected element.

Tests cover every new upstream row/column example, dimension order, inferred
sizes, scaling, and three-dimensional access. Upstream's permissive assignment
checks still allow treating a multidimensional array address as `int *` to
inspect its flat storage. Dimensions are numeric literals and bounds are
unchecked. No new intentional Python/C difference is introduced.

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
