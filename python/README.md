# Lesson 82: Bitwise complement

Original chibicc commit: [`46a96d6862e4c1317ff48df69391fd98a1ae5e3d`](https://github.com/rui314/chibicc/commit/46a96d6862e4c1317ff48df69391fd98a1ae5e3d).
Earlier explanations are available in Git history.

## What changed

Unary ~ creates a BITNOT node and emits `not %rax`, flipping each bit of the
register. Thus ~0 is -1 and ~-1 is zero. Logical ! checks zero; bitwise ~ changes
the integer representation. The parser gives it unary precedence.

This original commit retains the operand's type instead of applying C's full
integer promotion rules: sizeof(~(char)0) is still 1 here. It also always emits a
64-bit not. Python preserves those stages and emits assembly rather than using
Python's own arbitrary-precision bitwise complement for runtime computation.

## Assembly and WSL example

```sh
printf 'int main(){return ~0;}\n' > /tmp/lesson82.c
python3 python/main.py /tmp/lesson82.c > /tmp/lesson82.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson82 /tmp/lesson82.s
/tmp/lesson82
echo $?
```

`mov $0, %rax` followed by `not %rax` produces all one bits (-1). The shell shows
255 because process exit statuses retain only the low eight bits. Tests check
both signs, repeated complement, long values, historical sizeof/type behavior,
assembly, real execution, and updated original programs.

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
