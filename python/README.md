# Lesson 66: Binary register widths

Original chibicc commit: [`cb81a379d9f7aef32fb1bbebd18f8618e1617a3f`](https://github.com/rui314/chibicc/commit/cb81a379d9f7aef32fb1bbebd18f8618e1617a3f).
Earlier explanations are available in Git history.

## What changed

Binary addition, subtraction, multiplication and comparison now select register
width from the left operand's type. Long and pointer/array operands use
`%rax`/`%rdi`; char, short and int use `%eax`/`%edi`. Signed division uses
`cqo` and a sixty-four-bit divisor for an eight-byte left operand, otherwise
`cdq` and a thirty-two-bit divisor. Stack temporaries remain eight bytes.

A write to eax clears the high half of rax, while signed comparisons interpret
the low thirty-two bits with the chosen width. This matches the original
commit's intermediate lowering; mixed-type conversions are not complete yet.
In particular, current literals and calls are long, and negative computed int
values are not always extended before wider use. Negative variable pointer
indices are another limitation until conversion rules are added.

Python emits the same width choices as C. The multiplication overflow test
checks this machine's low-bit result; signed overflow is not a portable C
guarantee. The code generator expects type-annotated binary operands, so its
hand-built invalid-node test now supplies the operand types explicitly.

## Assembly and WSL example

```sh
printf 'int main(){int x=7,y=3;return (x+y)*(x-y)/y;}\n' > /tmp/lesson66.c
python3 python/main.py -o /tmp/lesson66.s /tmp/lesson66.c
cat /tmp/lesson66.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson66 /tmp/lesson66.s
/tmp/lesson66
echo $?
```

`add %edi, %eax`, `sub %edi, %eax`, and `imul %edi, %eax` compute
10 times 4. `cdq` prepares edx:eax for `idiv %edi`, yielding 13. The shell
shows status 13. Replacing int with long selects rax/rdi and cqo instead.
Tests check those exact operations, signed divisions and comparisons for all
integer widths, low-bit multiplication, pointer arithmetic, and the complete
upstream C fixtures. Existing pure-literal arithmetic remains sixty-four bit.

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
