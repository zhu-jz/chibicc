# Lesson 212: Update bitfields with compound assignments

Original chibicc commit: [`54c2b3b18fb80235ad9ee53cac3966e8aad9e12a`](https://github.com/rui314/chibicc/commit/54c2b3b18fb80235ad9ee53cac3966e8aad9e12a).
Earlier explanations are available in Git history.

Member compound assignments now save a pointer to the containing aggregate,
then read and assign its member through that pointer. This preserves bitfield
metadata and evaluates the base only once. Prefix/postfix increments use the
same rewriting. Ordinary member updates follow this path too.

Bitfield stores also preserve their expression result in r8 while merging the
storage unit. Python builds explicit nodes with a shared temporary object
instead of the C pointer-based constructors.

```sh
printf 'int main(void){struct T{int a:10,b:10;}x={1,2};return x.b+=40;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly extracts b, adds 40, merges the updated bits and restores the value
from r8 to rax. Tests cover arithmetic and shifts, prefix/postfix results,
ordinary assignment results, side-effecting bases, neighbor preservation and
upstream fixtures. The original returns the assigned value before truncating
it to the bitfield width; we retain that behavior at this step.

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
