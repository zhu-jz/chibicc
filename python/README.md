# Lesson 271: Allocate dynamic stack storage with alloca

Original chibicc commit: [`77275c546a5340f94ad011cd759ef162bc714ba6`](https://github.com/rui314/chibicc/commit/77275c546a5340f94ad011cd759ef162bc714ba6).
Earlier explanations are available in Git history.

The parser predeclares alloca(int) returning void*. Every function now keeps a
bookkeeping pointer in a local named __alloca_size__. A direct
alloca call generates stack-allocation code instead of a call to a library symbol.
Requests round up to 16 bytes, preserving stack alignment for subsequent calls.

```sh
printf 'int main(void){char *p=alloca(3);p[0]=12;p[2]=30;return p[0]+p[2];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The prologue saves the bottom of the fixed frame. Allocation lowers rsp and moves
any temporary expression bytes to their new stack position, then lowers the
saved bottom and returns that address in rax. Stores into the allocated memory
hold 12 and 30; their sum returns 42. The normal epilogue restores rsp from rbp,
releasing all allocations at function return. Storage does not survive that return.
Tests cover alignment, repeated allocations, a pending arithmetic temporary,
alloca inside another call's arguments, single evaluation, separate functions,
copy-loop assembly and the original alloca.c fixture.
Python stores the bookkeeping Obj reference explicitly; C uses a pointer field.
The original int parameter and 32-bit alignment mask are retained, so arbitrary
64-bit or negative allocation sizes are not promised. Every function's fixed
frame now includes the bookkeeping slot, even if it never calls alloca.
Older declaration-focused tests exclude that slot when inspecting source locals;
frame-size and assembly snapshots include its actual storage and initialization.

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
