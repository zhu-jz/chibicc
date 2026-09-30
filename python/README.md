# Lesson 85: Short-circuit logical operators

Original chibicc commit: [`f30f78175c1fd50c8cdd132ca804573ae0d18453`](https://github.com/rui314/chibicc/commit/f30f78175c1fd50c8cdd132ca804573ae0d18453).
Earlier explanations are available in Git history.

## What changed

&& and || produce int 0 or 1 and evaluate left to right. && skips its right
operand when the left is zero; || skips it when the left is nonzero. The parser
places && below bitwise | and above ||, with assignment lower still. Separate
LOGAND/LOGOR nodes emit conditional jumps instead of the normal binary push/pop
sequence, preserving side effects and avoiding unwanted evaluation.

Python's shared label counter supplies unique assembly labels, as C's counter
does. The original still compares full rax for truth tests; this step preserves
that limitation with narrow expressions whose upper bits are stale.

## Assembly and WSL example

```sh
printf 'int main(){int x=42;0&&++x;return x;}\n' > /tmp/lesson85.c
python3 python/main.py /tmp/lesson85.c > /tmp/lesson85.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson85 /tmp/lesson85.s
/tmp/lesson85
echo $?
```

A zero comparison branches to `.L.false.N` before the increment instructions.
The program returns 42 because ++x is skipped. || instead branches on nonzero
to `.L.true.N`. Tests cover skipped and evaluated effects, guarded null-pointer
dereferences, normalized results, precedence, label uniqueness, and upstream
programs. Both operands are parsed and typed even when one is skipped at runtime.

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
