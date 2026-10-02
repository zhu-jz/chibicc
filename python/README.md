# Lesson 308: Atomic exchange

Original chibicc commit: [`80ea9d427c5041415b014a0a97193f1f7e0a871b`](https://github.com/rui314/chibicc/commit/80ea9d427c5041415b014a0a97193f1f7e0a871b).
Earlier explanations are available in Git history.

`atomic_exchange(&value, replacement)` atomically replaces a value and returns
its old contents. An `EXCH` node holds the pointer and value. Its result type is
the pointed-to type; assembly evaluates the pointer first and the value second,
once each. Memory-form `xchg` supplies atomicity without a separate `lock` prefix.
The accumulator register width follows the object's size.

The `_explicit` macro discards its order argument, just as the original header
does here. No memory-order enum exists yet. This historical implementation adds
no extra sign extension after narrow exchanges; high accumulator bits follow
the emitted instruction. Python gives a located pointer diagnostic where the
original error path accidentally dereferences an unset `cas_addr` field, and
reports unsupported widths instead of an internal assertion.

```sh
cat >/tmp/lesson.c <<'C'
#include <stdatomic.h>
int main(void) {
  int value = 7;
  int old = atomic_exchange(&value, 42);
  return old == 7 ? value : 1;
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Tests check returned and stored values for 1/2/4/8-byte objects, assembly widths,
single evaluation of operands, ignored order arguments, and bad pointers.
The original atomic test now also exercises both exchange outcomes.

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
