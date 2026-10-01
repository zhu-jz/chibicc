# Lesson 220: Expose anonymous struct and union members

Original chibicc commit: [`c3075b3030c0488df1e7aa9f600da0f66072186b`](https://github.com/rui314/chibicc/commit/c3075b3030c0488df1e7aa9f600da0f66072186b).
Earlier explanations are available in Git history.

A struct or union member declaration ending immediately in a semicolon can
now create an unnamed aggregate member. Its children are visible in the
outer member namespace. Lookup searches such members recursively and builds
a chain of MEMBER nodes, preserving every intermediate byte offset.

```sh
printf 'int main(void){struct T{struct{int a;};int b;}x={{12},30};return x.a+x.b;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The chained address calculation reaches a in the inner struct. Ordinary loads
and addition return 42. Existing aggregate initialization supplies nested values.
Tests cover multiple levels, anonymous union byte views, global initializers,
arrow access, nested bitfield updates, missing names and original fixtures.
Python represents an absent name with None and safely skips unnamed scalar
members during lookup; C uses null pointers. Ambiguity diagnostics and designated
initializers are not introduced by this original commit.

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
