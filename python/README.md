# Lesson 141: Floating-point comparisons

Original chibicc commit: [`cf9ceecb2f8cad2fb694b15c14ca1cf98e9524e7`](https://github.com/rui314/chibicc/commit/cf9ceecb2f8cad2fb694b15c14ca1cf98e9524e7).
Earlier explanations are available in Git history.

## What changed

Floating operands now have common-type precedence: double wins over float,
and either wins over integer. Comparisons save the right value in an eight-byte
stack slot, evaluate the left in xmm0, restore the right to xmm1, and use ucomiss
or ucomisd. Their result is still an ordinary int in rax.

NaN comparisons require the parity flag: equality combines sete with setnp,
while inequality combines setne with setp. Ordered < and <= use seta/setae because
the emitted comparison's operands are reversed. The floating push/pop helpers
update the same depth counter used for call alignment. Python loops and emitted
instruction lists preserve the original behavior without host-side evaluation.

This step adds comparisons; other floating binary operations still report
invalid expression. General floating condition checks and argument ABI handling
remain incomplete. Tests construct NaN by a union bit pattern without arithmetic.

## Assembly and WSL example

```sh
printf 'int main(void){return 4.9<=5.0f;}\n' > /tmp/lesson141.c
python3 python/main.py /tmp/lesson141.c > /tmp/lesson141.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson141 /tmp/lesson141.s
/tmp/lesson141
echo $?
```

The float operand converts to double, the emitter compares in xmm registers,
and setae records that the right value is at least the left. Exit status is 1.
Tests cover mixed numeric types, a floating no-argument return, every NaN
comparison, floating stack preservation, exact parity-sensitive assembly,
actual execution, and expanded original floating examples.

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
