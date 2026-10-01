# Lesson 202: Call functions returning aggregates

Original chibicc commit: [`c72df1c9be535bdfd5b46609996bf1eaf540aced`](https://github.com/rui314/chibicc/commit/c72df1c9be535bdfd5b46609996bf1eaf540aced).
Earlier explanations are available in Git history.

The parser allocates an anonymous local return buffer for each aggregate call.
Small results arrive in rax/rdx and xmm0/xmm1 according to their byte-range
classes, then get copied into that buffer. The expression leaves its address
in rax so member access and aggregate assignment work as usual.

Large results use a hidden first argument: the caller passes the return
buffer address in rdi, moving other arguments one GP register along. This
commit implements the caller only; GCC helpers supply aggregate-returning
functions. Python stores the buffer object directly on the call node.

```sh
printf 'struct T{long a,b,c;};struct T f(void);int main(void){struct T x=f();return x.a+x.b+x.c;}\n' > /tmp/lesson.c
printf 'struct T{long a,b,c;};struct T f(void){return (struct T){12,15,15};}\n' > /tmp/helper.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s /tmp/helper.c
/tmp/lesson
echo $?  # 42
```

The hidden rdi points into main's frame. GCC fills that memory and returns
its address in rax. Tests check both mixed chunk orders, floating chunks,
tiny structs, unions, large results, hidden-argument register pressure,
member access, assignment, and the original C fixtures.

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
