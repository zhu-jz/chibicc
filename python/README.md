# Lesson 218: Align large array variables to sixteen bytes

Original chibicc commit: [`5257ee0f202a5f9c4e5bcb576646cefe70f3ae91`](https://github.com/rui314/chibicc/commit/5257ee0f202a5f9c4e5bcb576646cefe70f3ae91).
Earlier explanations are available in Git history.

Local and global array variables occupying at least sixteen bytes now request
alignment of at least sixteen bytes. A larger explicit alignment is preserved.
The array type itself keeps its element alignment, so _Alignof(char[17]) is
still 1. Local slot allocation applies the stronger variable alignment, and
global assembly uses a stronger .align directive.

```sh
printf 'int main(void){char x[17];return (unsigned long)&x%%16+42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The local array starts at a frame offset divisible by sixteen; rbp is aligned
too, so the remainder is zero. Tests run four large lengths, explicit 32-byte
alignment, unchanged type alignment, global directives and original fixtures.
Python uses max and integer alignment arithmetic. This commit changes the
alignment value only; the original placement of global .align before the
section directive is retained and can affect globals when sections change.
Larger explicit local alignments round the frame offset; the prologue still
guarantees only sixteen-byte frame-base alignment, as in the original.

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
