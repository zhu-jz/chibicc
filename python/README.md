# Lesson 313: Packed structure layout

Original chibicc commit: [`44bea4c85a48d440bc0f704abe64eac80e9165dc`](https://github.com/rui314/chibicc/commit/44bea4c85a48d440bc0f704abe64eac80e9165dc).
Earlier explanations are available in Git history.

`__attribute__((packed))` is accepted immediately after `struct` or after the
closing brace of its definition. The type records `is_packed`; ordinary members
are laid out consecutively without aligning each offset, and the structure's
alignment remains 1. A `char` followed by an `int` therefore occupies five bytes,
with the `int` at byte offset 1. x86-64 can load and store this unaligned integer.

```sh
cat >/tmp/lesson.c <<'C'
struct __attribute__((packed)) Pair { char a; int b; };
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

Assembly adds the member's one-byte offset to its base address before loading
the integer. Unpacked structures retain normal padding. This commit recognizes
only the exact `packed` spelling, and it retains previous bitfield rules and
union layout. An attribute on a reference to an existing tag does not alter
that type. Python updates an existing type object to preserve forward pointers,
matching the original C overwrite behavior.
Tests cover both attribute positions, sizes, offsets, alignment, initialization,
forward tags, ordinary layout and unsupported attributes; the unchanged original
`attribute.c` fixture is also compiled and run.

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
