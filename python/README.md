# Lesson 215: Buffer assembly before writing output

Original chibicc commit: [`2bdc6b800c1dbe6db584b91046785d4c48c41fb2`](https://github.com/rui314/chibicc/commit/2bdc6b800c1dbe6db584b91046785d4c48c41fb2).
Earlier explanations are available in Git history.

This original commit prevents code-generation errors from leaving partial
assembly files. The Python port already accumulates instructions in a list
and returns a complete string before write_output opens the destination, so
we retain that design and add explicit regression coverage for the guarantee.
A comment marks the boundary in cc1; no second buffering abstraction is needed.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The completed buffer contains main's mov $42 and return instructions. For
invalid code such as return &1, generation raises not an lvalue before the
output is opened. Tests verify an existing output stays intact, an absent one
stays absent, stdout has no partial assembly and a successful output is complete.
As in the original, the final file write is not an atomic rename: failure during
that write itself can still leave partial data. -E behavior is unchanged.

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
