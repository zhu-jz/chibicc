# Lesson 49: Anonymous structs and member access

Original chibicc commit: [`f814033d04c4cefdbcf8174d65011d484d69303c`](https://github.com/rui314/chibicc/commit/f814033d04c4cefdbcf8174d65011d484d69303c).
Earlier explanations are available in Git history.

## What changed

`struct { ... }` builds a STRUCT type containing members in declaration order.
Each Member has its type, name token, and byte offset. At this stage members
are packed without padding: char is one byte and int is eight, so
`struct {char a; int b;}` has offsets 0 and 1 and total size 9. Anonymous
structs can contain arrays and other structs and can themselves be array
elements or global variables. Struct tags and `->` are not supported yet.

Postfix parsing accepts `.` alongside subscripts. It checks that the left
operand is a struct and finds the named member. The MEMBER node inherits that
field's type. To get its address, codegen gets the containing struct's address
and adds the member offset; the usual typed load/store handles the field.
For `x.a.b`, address generation recursively adds both offsets. Array members
retain their addresses rather than loading an entire array.

Python stores members in a list of dataclasses instead of C's linked records.
This first struct lesson does not implement aggregate copying or struct call
ABI rules. Its packed layout also differs from GCC's normal aligned layout;
our test helper receives scalar assertion results, not struct values.

## Assembly and WSL example

```sh
printf 'int main(){struct {char a;int b;} x; x.b=42; return x.b;}\n' > /tmp/lesson49.c
python3 python/main.py -o /tmp/lesson49.s /tmp/lesson49.c
cat /tmp/lesson49.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson49 /tmp/lesson49.s
/tmp/lesson49
echo $?
```

`lea offset(%rbp), %rax` finds x, and `add $1, %rax` finds b. Storing/loading
that eight-byte field uses the existing integer instructions. The shell
reports 42; the executable itself prints nothing. The new upstream struct
fixture checks member reads/writes, arrays, nested structs, sizeof, and empty
structs. Additional tests check globals, taking a member's address, exact
layout, and the `not a struct` / `no such member` diagnostics.

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
