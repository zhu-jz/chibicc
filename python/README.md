# Lesson 310: Complete the atomic header

Original chibicc commit: [`0a5d08c8f8a72e39828e7b1910c55174e6c8dd5e`](https://github.com/rui314/chibicc/commit/0a5d08c8f8a72e39828e7b1910c55174e6c8dd5e).
Earlier explanations are available in Git history.

This original commit expands `stdatomic.h` with atomic typedefs, the memory-order
enum, flag operations, load/store and fetch macros, lock-free constants, and
initialization helpers. It also removes `__STDC_NO_ATOMICS__` from predefined
macros. The header is copied intact; its expansions use the compiler features
from the preceding lessons.

The enum runs from relaxed (0) to sequentially consistent (5). At this point
order arguments are ignored, fence macros expand to nothing, and lock-free
queries/constants are 1. Fetch macros expand to compound assignments and return
the **new** value, unlike the standard C old-value contract. `ATOMIC_FLAG_INIT`
is a function-like macro taking one argument. These are original limitations,
not Python changes; this lesson deliberately preserves them.

```sh
cat >/tmp/lesson.c <<'C'
#include <stdatomic.h>
int main(void) {
  atomic_int value;
  atomic_init(&value, 7);
  atomic_fetch_add(&value, 35);
  return atomic_load(&value);
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The fetch expansion reaches the `lock cmpxchg` retry loop; the final load reads
the value into the accumulator before returning. Tests exercise header macros,
flags, typedef sizes, enum values, ignored arguments, and the removed predefined
macro. Python has no additional semantic difference for this header-only step.

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
