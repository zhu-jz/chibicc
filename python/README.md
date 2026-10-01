# Lesson 274: Compute sizeof for a fresh VLA type

Original chibicc commit: [`2fa8f489f3a852bd5bb17e023fdc5ea3a606100d`](https://github.com/rui314/chibicc/commit/2fa8f489f3a852bd5bb17e023fdc5ea3a606100d).
Earlier explanations are available in Git history.

sizeof can now create a runtime-sized array type directly, such as sizeof(int[n]).
If that type has no saved size yet, the parser builds a comma expression: compute
and save its dimension sizes, then read the final byte size. Existing VLA types
continue using their previously computed size. No array storage is allocated just
to calculate sizeof a type.

```sh
printf 'int main(void){int n=5;return sizeof(int[2][n])+2;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly multiplies n by four bytes and then by two rows, saves and loads 40,
and adds 2 before returning. Tests also check that a side-effecting bound runs
once and that sizeof(typeof(existing_array)) retains its declaration-time size.
Python represents C's linked expression nodes with dataclasses; the runtime
calculation and saved-size behavior follow the original commit.

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
