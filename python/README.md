# Lesson 309: Atomic types and compound updates

Original chibicc commit: [`d69a11dd25a77c2b9390e54c9f9e8967456cb642`](https://github.com/rui314/chibicc/commit/d69a11dd25a77c2b9390e54c9f9e8967456cb642).
Earlier explanations are available in Git history.

`_Atomic int`, `int _Atomic`, and `_Atomic(int)` mark a copied type as atomic.
Copying preserves the ordinary shared `int` type. Atomic `++`, `--`, and `op=`
reuse the earlier compound-assignment parser but build a statement expression:

```c
/* Conceptual expansion of A += B */
T *address = &A;
U value = B;
T old = *address, replacement;
do {
  replacement = old + value;
} while (!__builtin_compare_and_swap(address, &old, replacement));
/* expression result: replacement */
```

A failed `lock cmpxchg` refreshes `old`, so the next iteration recomputes from
the value another thread installed. Address and right-hand value are evaluated
once, before retrying. Existing postfix lowering subtracts the increment from
the successful result to recover the old value.

```sh
cat >/tmp/lesson.c <<'C'
int main(void) {
  _Atomic(int) value = 7;
  value += 35;
  return value;
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

This commit covers compound updates. Plain atomic assignment still uses the
existing store here. The original member/bitfield lowering runs before the
atomic branch, so atomic structure members are not changed into retry loops by
this step. These historical limits remain visible. Python uses lists for the
new statement sequence and explicit temporary objects instead of C linked nodes.
Tests cover qualifier forms, operators, prefix/postfix values, side effects,
type isolation, assembly, and the updated original four-thread test, whose
expected combined counter is six million.

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
