# Lesson 74: Enumerations

Original chibicc commit: [`48ba2656fecc646ec4eb7f943fa94b02ed9725c7`](https://github.com/rui314/chibicc/commit/48ba2656fecc646ec4eb7f943fa94b02ed9725c7).
Earlier explanations are available in Git history.

## What changed

Enum variables have four-byte size and alignment. Enumerator names enter the
ordinary identifier scope and become numeric expression nodes without runtime
storage. Values begin at zero and increment; a numeric token after = resets the
sequence. Enum tags share the tag namespace with struct/union tags. Tagged enum
references must already exist and have enum kind.

The historical grammar accepts numeric tokens rather than constant expressions:
negative expressions and trailing commas are not supported yet. Python stores
counter values as arbitrary-precision ints, so values beyond C int's range are
not a portable match; this lesson's supported examples stay within signed int.

## Assembly and WSL example

```sh
printf 'enum E{zero,five=5,six};int main(){enum E x=six;return x;}\n' > /tmp/lesson74.c
python3 python/main.py /tmp/lesson74.c > /tmp/lesson74.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson74 /tmp/lesson74.s
/tmp/lesson74
echo $?
```

The enumerator six becomes `mov $6, %rax`, then x is stored with eax as a
four-byte object. The program exits with 6. Tests check numbering, scope and
shadowing, tag/type errors, sizeof, assembly, executable status, and original C
tests. Constants allocate no stack slots or global data.

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
