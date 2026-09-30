# Lesson 55: Struct and union assignment

Original chibicc commit: [`bef05432c9d3289636ed1d360ca9b863a0698dc7`](https://github.com/rui314/chibicc/commit/bef05432c9d3289636ed1d360ca9b863a0698dc7).
Earlier explanations are available in Git history.

## What changed

A struct or union can be too large for a register. Loading an aggregate now
leaves its storage address in `%rax`, as array expressions already did.
For aggregate assignment, codegen pops the destination address into `%rdi`
and emits a byte load/store pair for every byte in the destination type.
`%rax` still points to the source, and `%r8b` carries each byte during copying.
All bytes, including padding, are copied.

This supports `y=x`, assignments through pointers, initialization from another
aggregate, and chains such as `z=y=x`. No Python memory copy runs at compile
time: Python emits the real x86-64 copy instructions, just as upstream C does.
Arrays still cannot be assigned directly, and aggregate function argument /
return ABI rules and assignment type compatibility remain incomplete.

## Assembly and WSL example

```sh
printf 'int main(){struct t{int a,b;} x,y;x.a=20;x.b=22;y=x;return y.a+y.b;}\n' > /tmp/lesson55.c
python3 python/main.py -o /tmp/lesson55.s /tmp/lesson55.c
cat /tmp/lesson55.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson55 /tmp/lesson55.s
/tmp/lesson55
echo $?
```

After obtaining both addresses, the copy includes pairs such as
`mov 0(%rax), %r8b` and `mov %r8b, 0(%rdi)`, up through byte 15.
The final field loads add 20 and 22, returning status 42. The executable
prints nothing. Tests cover the upstream struct/union assignments, pointer
copies, chains, a seventeen-byte object, padding bytes, globals, initialization
and self-assignment. A small assembly check ensures exactly the required bytes
are copied, and all updated upstream C fixtures run as executables.

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
