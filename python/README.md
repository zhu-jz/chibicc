# Lesson 81: Logical negation

Original chibicc commit: [`6b88bcb306ef80b65d7f99c081ba83283b4ffac5`](https://github.com/rui314/chibicc/commit/6b88bcb306ef80b65d7f99c081ba83283b4ffac5).
Earlier explanations are available in Git history.

## What changed

Unary ! evaluates its operand and returns int 1 for zero or int 0 for nonzero.
It parses at unary precedence and has a NOT node. The emitter compares rax with
zero, then materializes the equality flag as an integer. Pointers and longs use
the same zero test. No Python truth-value evaluation implements compiled logic.

This original commit compares the full rax even for int operands; together with
the still-incomplete long-to-int cast, that can expose leftover upper bits.
The historical emitter is preserved rather than changing conversion semantics.

## Assembly and WSL example

```sh
printf 'int main(){return !0;}\n' > /tmp/lesson81.c
python3 python/main.py /tmp/lesson81.c > /tmp/lesson81.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson81 /tmp/lesson81.s
/tmp/lesson81
echo $?
```

`cmp $0, %rax` sets flags, `sete %al` writes 1 when equal, and
`movzx %al, %rax` clears the remaining bits. Main returns 1. Tests cover zero,
nonzero, repeated negation, pointers, large longs, result type/sizeof, assembly,
executable statuses, and all updated original fixture programs.

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
