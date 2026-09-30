# Lesson 90: Labels may share typedef names

Original chibicc commit: [`a4be55b333c9f712c334aac81e7ef4e076c2bc9b`](https://github.com/rui314/chibicc/commit/a4be55b333c9f712c334aac81e7ef4e076c2bc9b).
Earlier explanations are available in Git history.

## What changed

A compound statement checks for a following colon before interpreting a known
type name as a declaration. Thus a typedef named T can coexist with the label
T:. The statement parser recognizes the label, while later `T x;` still uses the
typedef. This is a parsing ambiguity fix: labels have a separate namespace.
No type-system or code-generation change is needed.

Python checks the next token by list index; C checks tok->next. Tests preserve
the shared label name and verify both declaration parsing and executable results.

## Assembly and WSL example

```sh
printf 'typedef int T;int main(){goto T;T:return 42;}\n' > /tmp/lesson90.c
python3 python/main.py /tmp/lesson90.c > /tmp/lesson90.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson90 /tmp/lesson90.s
/tmp/lesson90
echo $?
```

The typedef emits no instructions. goto emits a jump to the unique assembly label
for T:, and the return loads 42. The shell displays 42. Tests exercise global and
local typedefs, continued use of the typedef after the label, tree/assembly label
matching, prior goto behavior, and the updated upstream control tests.

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
