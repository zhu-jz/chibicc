# Lesson 102: Local struct initializers

Original chibicc commit: [`e9d2c46ab3cc8b8518df289a4fc24a9e3fc9b3fe`](https://github.com/rui314/chibicc/commit/e9d2c46ab3cc8b8518df289a4fc24a9e3fc9b3fe).
Earlier explanations are available in Git history.

## What changed

Struct initializers now allocate a child initializer for each member, indexed
in declaration order. Brace lists fill those children; omitted members remain
zero and excess supplied values are discarded. A designation path may contain
a Member as well as array indices, so lowering can assign nested struct fields,
arrays within structs, and members of structs within arrays. Existing MEMBER
address generation applies each member's aligned offset.

Python lists replace indexed child-pointer storage and InitDesg.member identifies
a member path. This original commit temporarily requires braces for every struct
initializer, rejecting the previously supported `struct T b=a;` form. Ordinary
struct assignment remains supported; the older copy test now uses that form.
Union brace initialization and complete aggregate syntax are still unavailable.

## Assembly and WSL example

```sh
printf 'int main(){struct T{char a;int b;} x={1,42};return x.b;}\n' > /tmp/lesson102.c
python3 python/main.py /tmp/lesson102.c > /tmp/lesson102.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson102 /tmp/lesson102.s
/tmp/lesson102
echo $?
```

The emitter clears x, stores one byte for a, then adds b's aligned offset four
and stores 42 with eax. Main exits with 42. Tests cover partial/empty structs,
nested aggregates, arrays of structs with inferred lengths, member ordering,
padding zeroing, expression-initializer rejection, assembly offsets, real
execution, and the updated original initializer program.

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
