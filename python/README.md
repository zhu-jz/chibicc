# Lesson 255: Compare types with a compiler builtin

Original chibicc commit: [`1433b404d68f9fe314ae2955d0988dd74e5ecb92`](https://github.com/rui314/chibicc/commit/1433b404d68f9fe314ae2955d0988dd74e5ecb92).
Earlier explanations are available in Git history.

`__builtin_types_compatible_p(T,U)` now produces an integer constant telling
whether two types are compatible. Pointer and function types compare recursively;
structs and unions keep declaration identity. Copies of a type remember their
origin so names added by declarators do not make the underlying type different.

```sh
printf 'typedef struct{int a;}T;int main(void){return __builtin_types_compatible_p(T,const T)?42:0;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The builtin becomes 1 during parsing; assembly takes the true branch and returns
42. No runtime type descriptors or comparison calls are emitted. Tests cover
signedness, qualifiers, pointer depth, function parameters and variadic status,
distinct anonymous structs, typedef identity, arrays and the new builtin.c fixture.
Python uses object identity and an origin reference instead of C pointer identity.
The original array rule has a historical bug: separately constructed fixed-size
arrays compare false, while equal incomplete arrays compare true. We preserve
and test that exact rule rather than silently correcting a later-history issue.

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
