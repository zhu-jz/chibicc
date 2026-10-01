# Lesson 98: Zero omitted initializer elements

Original chibicc commit: [`ae0a37dc4b39018a95616836ae4aaf4c8bfd779b`](https://github.com/rui314/chibicc/commit/ae0a37dc4b39018a95616836ae4aaf4c8bfd779b).
Earlier explanations are available in Git history.

## What changed

Array initializer lists may end before filling every element, including an empty
list. The parser first builds a MEMZERO expression for the whole local object,
then emits assignments for the provided leaves. Missing leaves become NULL_EXPR
and generate no assignment. Nested omitted arrays remain zero because the entire
object was cleared. All explicit local initializers, even scalar ones, take this
zero-then-assign path in the original commit.

The emitter implements clearing with rep stosb: rcx is the byte count, rdi is the
address, and al is zero. Python emits that instruction instead of clearing a
Python data structure. Grammar-only test comparisons strip generated casts and
initialization clearing; dedicated tests inspect the actual MEMZERO tree and
instructions, and execute programs to check omitted elements. Excess supplied
elements and trailing commas are still rejected at this stage.

## Assembly and WSL example

```sh
printf 'int main(){int a[3]={42};return a[0]+a[1]+a[2];}\n' > /tmp/lesson98.c
python3 python/main.py /tmp/lesson98.c > /tmp/lesson98.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson98 /tmp/lesson98.s
/tmp/lesson98
echo $?
```

`mov $12, %rcx`, `lea ...(%rbp), %rdi`, `mov $0, %al`, and `rep stosb` clear all
twelve bytes before a[0] receives 42. The omitted elements load zero, so the shell
displays 42. Tests cover empty and nested partial lists, neighboring objects,
clearing before user expressions, tree metadata, assembly, original initializer
programs, and the complete existing regression suite.

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
