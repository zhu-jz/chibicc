# Lesson 59: Parenthesized type declarators

Original chibicc commit: [`a817b23da3c6f39f22bc57c0a53169978d97d7fa`](https://github.com/rui314/chibicc/commit/a817b23da3c6f39f22bc57c0a53169978d97d7fa).
Earlier explanations are available in Git history.

## What changed

The declarator grammar now accepts parentheses recursively. Stars before a
name and suffixes after it need the correct grouping: `char *x[3]` is an
array of three char pointers (24 bytes), whereas `char (*x)[3]` is a pointer
to an array of three chars (8 bytes). `char (x[3])[4]` describes an array of
three arrays of four chars, with total size 12.

Following upstream, the parser first reads the inner declarator using a dummy
type to locate `)`. It then applies the suffix after that parenthesis to the
real base type, and reparses the inner declarator around that completed type.
Python returns type/token-index pairs in place of C's output pointer. The
dummy type is discarded; no variable storage is allocated during these passes.

This changes type construction, not expression grouping or codegen. Nested
declarations do not themselves enable calls through function pointers, and
this stage's simplified address-of-array and assignment compatibility rules
still apply.

## Assembly and WSL example

```sh
printf 'int main(){int a[2][3];int (*p)[3]=a;p[1][2]=42;return a[1][2];}\n' > /tmp/lesson59.c
python3 python/main.py -o /tmp/lesson59.s /tmp/lesson59.c
cat /tmp/lesson59.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson59 /tmp/lesson59.s
/tmp/lesson59
echo $?
```

p points to a row of three four-byte ints. The first subscript scales by 12,
and the second by 4; the existing address arithmetic and int load/store find
the same element as a[1][2]. The shell displays 42. Tests inspect the two
pointer/array shapes and nested dimensions, execute pointer-to-array and
parameter examples, check a parenthesized function name and missing `)`, and
run all upstream C fixtures with the updated variable examples.

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
