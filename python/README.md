# Lesson 143: Floating conditions

Original chibicc commit: [`0ce109302715f8186b90671a53517a63a2741022`](https://github.com/rui314/chibicc/commit/0ce109302715f8186b90671a53517a63a2741022).
Earlier explanations are available in Git history.

## What changed

The shared zero-comparison helper now handles float and double, and all condition
sites call it. Integer conditions compare eax or rax according to their type;
floating conditions zero xmm1 with xorps/xorpd and compare xmm0 using ucomiss/ucomisd.
Conditional branches, logical operators, and Boolean casts use the resulting flags.
Short circuit evaluation still skips the right operand when appropriate.

The Python implementation emits these instructions directly. Positive and negative
floating zero are false. This historical commit treats unordered NaN comparisons
as zero in truth tests because it uses the zero flag alone; tests deliberately
record this limitation instead of silently changing the original progression.

## Assembly and WSL example

```sh
printf 'int main(void){double x=0.5;if(x)return 42;return 1;}\n' > /tmp/lesson143.c
python3 python/main.py /tmp/lesson143.c > /tmp/lesson143.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson143 /tmp/lesson143.s
/tmp/lesson143
echo $?
```

ucomisd compares x against zero; je selects the false branch only when its zero
flag is set. Here x is nonzero, so main returns 42 in eax and the shell displays
exit status 42. The executable prints nothing itself. Tests cover both floating
widths, loops, short circuit side effects, signed zero, Boolean casts, historical
NaN behavior, emitted comparisons, execution, and the original C fixtures.

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
