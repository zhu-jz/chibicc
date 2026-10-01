# Lesson 210: Pack named bitfields into storage units

Original chibicc commit: [`cc852fe99d0acfc6d547b36c75ff85e90975ad36`](https://github.com/rui314/chibicc/commit/cc852fe99d0acfc6d547b36c75ff85e90975ad36).
Earlier explanations are available in Git history.

Members now record a bit width and offset. Struct layout counts bits, grouping
fields into storage units of their declared integer type and moving a crossing
field to the next unit. Ordinary members still start at their normal alignment.
A field read shifts its bits into place, then uses arithmetic right shift for
signed fields or logical right shift for unsigned fields.

Assignments load the current unit, clear the target mask, merge the new low
bits and store it back. This preserves neighboring fields. Local initializer
assignments automatically use that path. Python integer masks replace C's
long shifts; emitted operations still use x86-64 registers.

```sh
printf 'int main(void){struct T{unsigned int a:6,b:3;}x={42,7};return x.a;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Masking and merging initialize the shared word; shl/shr extract a and return
42 in rax. Tests cover signed truncation, unsigned reads, neighbor preservation,
crossing storage units, mixed ordinary members, layout metadata and the original
bitfield fixture. This first bitfield commit has no dedicated global initializer
support, unnamed-field rules or compound-assignment handling. Assignment results
still contain the merged storage unit, as in the original.

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
