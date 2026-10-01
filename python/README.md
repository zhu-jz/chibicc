# Lesson 207: Convert preprocessing numbers after expansion

Original chibicc commit: [`3f2c2d5bca4f4506e0ab0b03959d96be427fa672`](https://github.com/rui314/chibicc/commit/3f2c2d5bca4f4506e0ab0b03959d96be427fa672).
Earlier explanations are available in Git history.

The tokenizer now collects relaxed PP_NUM spellings without interpreting them.
After macro expansion, a conversion pass tries a complete integer first, then
a complete floating literal. It also converts keywords. Conditional directives
run this pass before evaluating their expression. Invalid surviving spellings
produce an invalid numeric constant diagnostic at the token location.

```sh
printf '#define CONCAT(x,y) x##y\nint main(void){int f0zz=34;return CONCAT(f,0zz)+0x1p3;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Macro pasting makes the identifier f0zz. The hexadecimal float becomes 8.0;
generated conversion/addition instructions return 42. Tests check raw token
spelling, identifier and decimal pasting, exponent signs, skipped invalid
numbers, conditional conversion, errors and original fixtures. Python uses
int, float and float.fromhex to decode literals only, then emits real assembly;
it keeps explicit 64-bit range errors rather than C strtoul overflow behavior.
Metadata and token identity survive conversion. The previous no-dot hexadecimal
float limitation is resolved in this original step.
The original fallback also accepts 08 as the double value 8.0; a regression
test records that historical behavior instead of treating it as valid octal.

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
