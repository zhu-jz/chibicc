# Lesson 201: Receive struct and union parameters

Original chibicc commit: [`d63b1f410a7aa3d308d0620d640f417a87b0c838`](https://github.com/rui314/chibicc/commit/d63b1f410a7aa3d308d0620d640f417a87b0c838).
Earlier explanations are available in Git history.

Aggregate parameters now use the same register/stack distinction on entry.
Small register chunks are saved into local slots; unusual GP chunk sizes use
byte stores and shifts, so a three-byte struct is handled without overwriting
its neighbor. Large aggregates have positive offsets in the incoming area.
Python factors the stores into straightforward methods instead of C switches.

```sh
printf 'struct T{int a;double b;};int sum(struct T x){return x.a+x.b;}int main(void){struct T x={12,30};return sum(x);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The caller puts the integer chunk in rdi and the double chunk in xmm0. The
callee stores them relative to rbp, accesses the members, and returns 42 in
rax. Tests cover mixed and floating aggregates, a tiny struct, a large stack
struct, unions, GCC callers, and the unchanged original C examples. This
historical classifier retains its boundary comparisons and its shifted second
range in parameter allocation; aggregate returns are still a later step.

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
