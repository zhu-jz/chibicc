# Lesson 314: Structure alignment attributes

Original chibicc commit: [`b35d148a8d8f7d9237173c70f18cd42d20f299ff`](https://github.com/rui314/chibicc/commit/b35d148a8d8f7d9237173c70f18cd42d20f299ff).
Earlier explanations are available in Git history.

Attribute parsing now accepts comma-separated `packed` and `aligned(N)` items,
repeated attribute groups, and constant expressions for `N`. Both positions
around a structure definition are supported. `aligned(8)` raises its alignment
and final size rounding; combining it with `packed` still keeps member offsets
consecutive. For `char a; int b;`, that combination gives offset 1 for `b`,
alignment 8, and total size 8.

```sh
cat >/tmp/lesson.c <<'C'
struct __attribute__((packed, aligned(8))) Pair { char a; int b; };
int main(void) {
  struct Pair value = { 1, 41 };
  return value.a + value.b;
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Code generation uses the computed size/alignment for storage and the unchanged
member offsets for loads. Unknown attribute names now report `unknown attribute`.
The original does not validate that alignment is a positive power of two; this
lesson retains that limitation. Python stores the evaluated alignment with C's
signed-int conversion, rather than letting an unbounded Python integer leak
into layout. Tests cover grouped/repeated attributes, both positions, packed
member offsets, aligned sizes, constant expressions, empty lists, and the
expanded original attribute fixture.

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
