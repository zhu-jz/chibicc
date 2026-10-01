# Lesson 110: Trailing commas in enum and initializer lists

Original chibicc commit: [`fde464c47cb69e030b58d8d204a508d6babd3e09`](https://github.com/rui314/chibicc/commit/fde464c47cb69e030b58d8d204a508d6babd3e09).
Earlier explanations are available in Git history.

## What changed

Enums and array/struct initializer lists now recognize both `}` and `,}` as
their end. Array-length inference counts the same elements with either ending.
Unbraced nested aggregates stop before the parent's trailing comma, leaving it
for the parent to consume. Union initialization optionally skips one comma.

Python returns the next token index from consume_end instead of updating C's
output pointer. The historical commit does not change scalar-brace parsing:
`int x={42,};` is still rejected, even though scalar braces without a trailing
comma work. Empty scalar and union braces remain unsupported.

## Assembly and WSL example

```sh
printf 'int main(){int a[]={1,2,42,};return a[2];}\n' > /tmp/lesson110.c
python3 python/main.py /tmp/lesson110.c > /tmp/lesson110.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson110 /tmp/lesson110.s
/tmp/lesson110
echo $?
```

The trailing comma emits nothing. The inferred array still occupies 12 bytes,
gets three int stores, and returns exit status 42. Tests cover arrays, structs,
unions, enums, brace elision, length inference, assembly sizing, scalar grammar
limits, and the original initializer suite.

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
