# Lesson 58: Two-byte short values

Original chibicc commit: [`9d48eef58b964551350fe0c1f641a57f5da40529`](https://github.com/rui314/chibicc/commit/9d48eef58b964551350fe0c1f641a57f5da40529).
Earlier explanations are available in Git history.

## What changed

Short is now accepted as a type with size/alignment 2. Scalar stores write
`%ax`, the low sixteen bits of `%rax`. Loads use `movswq` to sign-extend a
two-byte value into `%rax`. Parameter saves select `%di`, `%si`, `%dx`, `%cx`,
`%r8w`, or `%r9w` for short arguments. Arrays and pointer arithmetic use the
two-byte element size; struct fields and locals use two-byte alignment.

Thus `short x=32768;` stores bytes representing -32768, and reloading x gives
a negative sixty-four-bit value. Writing one short must not overwrite an
adjacent short. Char/int/long and pointer storage widths remain 1/4/8/8.
Python adds the ordinary Type singleton and instruction cases; no simulated
Python runtime evaluates the program.

Literal/comparison/function-call types remain long at this intermediate step,
and arithmetic conversions are still incomplete. The input range check from
lesson 57 and the existing compiler limits continue to apply.

## Assembly and WSL example

```sh
printf 'int main(){short x=42;return x;}\n' > /tmp/lesson58.c
python3 python/main.py -o /tmp/lesson58.s /tmp/lesson58.c
cat /tmp/lesson58.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson58 /tmp/lesson58.s
/tmp/lesson58
echo $?
```

x lives at -2(%rbp). `mov %ax, (%rdi)` stores two bytes and
`movswq (%rax), %rax` loads them for the return. The shell displays status
42; the executable prints nothing. Tests cover sizeof, truncation and signed
loads, neighboring values, globals, arrays, struct padding, all six short
parameters, and explicit assembly widths. Updated upstream function, struct
and variable fixtures are run with the existing C fixture suite.

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
