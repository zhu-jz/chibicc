# Lesson 307: Atomic compare-and-swap

Original chibicc commit: [`ca27455b92be2ffbfe58c7ffda623cf6ec112632`](https://github.com/rui314/chibicc/commit/ca27455b92be2ffbfe58c7ffda623cf6ec112632).
Earlier explanations are available in Git history.

The new builtin takes an object pointer, an expected-value pointer, and a
replacement value. Success stores the replacement and returns `_Bool` true.
Failure leaves the object alone, writes its observed value into `*expected`,
and returns false. Both header macros use this same instruction in this lesson.

The parser stores three operands in a `CAS` node. Type checking requires the
first two to be pointers. Assembly evaluates address, replacement, then expected
pointer, once each. `lock cmpxchg` compares memory with the accumulator and
atomically replaces it with `%dl`, `%dx`, `%edx`, or `%rdx` for 1/2/4/8 bytes.
`sete` captures success; the failure path copies the accumulator back through
`expected`. This step does not yet introduce the `_Atomic` type qualifier.
Python reports unsupported operand sizes instead of C's internal assertion.

```sh
cat >/tmp/lesson.c <<'C'
#include <stdatomic.h>
int main(void) {
  int value = 7, expected = 7;
  atomic_compare_exchange_strong(&value, &expected, 42);
  return value;
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42; main returns the value, it does not print it
```

Tests cover success, failure and expected-value updates at every supported
width, boolean size, operand evaluation, pointer diagnostics, and assembly.
The unchanged original pthread test increments a shared counter three million
times using a compare-and-swap retry loop.

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
