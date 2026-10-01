# Lesson 200: Pass struct and union arguments

Original chibicc commit: [`5e0f8c47e3bd91f589710a28f09b718d4a0ec6f3`](https://github.com/rui314/chibicc/commit/5e0f8c47e3bd91f589710a28f09b718d4a0ec6f3).
Earlier explanations are available in Git history.

Calls now copy aggregates instead of casting them to a scalar. Values larger
than sixteen bytes go on the stack, rounded to eight-byte slots. Smaller ones
are classified recursively in two eight-byte ranges: an all-floating range
uses XMM, and any integer or pointer member makes its range use a GP register.
Arrays and nested aggregates participate in the same classification.

The generated code copies each byte into a temporary stack area, then pops
register chunks into argument registers. Stack chunks stay until the call
returns. This commit changes callers only; GCC helper functions exercise the
receiving side. Python uses loops and lists instead of recursive C linked lists.
We retain this commit's strict register-limit comparisons and classification
of an empty second range; boundary cases await the corresponding original fix.

```sh
printf 'struct T{long a,b,c;};int f(struct T);int main(void){struct T x={12,15,15};return f(x);}\n' > /tmp/lesson.c
printf 'struct T{long a,b,c;};int f(struct T x){return x.a+x.b+x.c;}\n' > /tmp/helper.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s /tmp/helper.c
/tmp/lesson
echo $?  # 42
```

Here sub $24 reserves the aggregate copy, byte moves fill it, and the caller
removes thirty-two bytes including alignment padding after the call. Tests
cover mixed integer/double structs, floating arrays, a three-byte struct, a
large stack struct, a union, assembly cleanup, and the original C fixtures.

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
