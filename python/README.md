# Lesson 142: Floating arithmetic and negation

Original chibicc commit: [`83f76ebb66712a2560b2993e92265b574b1ab7ed`](https://github.com/rui314/chibicc/commit/83f76ebb66712a2560b2993e92265b574b1ab7ed).
Earlier explanations are available in Git history.

## What changed

Numeric addition/subtraction now accepts floating types as well as integers.
After common-type conversion, floating binary operations use addss/subss/mulss/
divss for float and addsd/subsd/mulsd/divsd for double. The existing floating
stack helpers preserve operands and call alignment. Negation toggles the IEEE
sign bit with xorps or xorpd, preserving signed zero and NaN payload bits.

This original commit also makes integer bitwise and/or/xor use eax/edi for
four-byte operands and rax/rdi for eight-byte operands. Python emits the same
instructions and operates on syntax trees; Python float is used only to decode
literals, not to execute the compiled arithmetic.

Floating division follows the target's usual SSE environment: zero divided by
zero produces NaN, which the comparison instructions handle. General floating
truth tests, floating argument-register handling, global floating initializers,
and floating constant-expression evaluation remain incomplete at this point in
the original history. These later features have not been prepared in advance.

## Assembly and WSL example

```sh
printf 'int main(void){double x=21.5;return x*2-1;}\n' > /tmp/lesson142.c
python3 python/main.py /tmp/lesson142.c > /tmp/lesson142.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson142 /tmp/lesson142.s
/tmp/lesson142
echo $?
```

The integer operands convert to double. mulsd computes 43.0, subsd gives 42.0,
and cvttsd2sil converts the return to int. The executable prints nothing; `echo $?`
shows its exit status 42. Tests cover both floating widths, mixed types, division,
negation, signed zero, NaN, result sizes, SSE arithmetic/sign instructions,
integer bitwise widths, real execution, and original float/sizeof examples.

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
