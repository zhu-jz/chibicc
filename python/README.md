# Lesson 131: Unsigned integer types and operations

Original chibicc commit: [`34ab83bdf49a23a47bc90354a5a4d22686d8d92a`](https://github.com/rui314/chibicc/commit/34ab83bdf49a23a47bc90354a5a4d22686d8d92a).
Earlier explanations are available in Git history.

## What changed

Unsigned char, short, int and long now have Type objects with an is_unsigned flag.
Small unsigned loads and function returns use zero extension. The cast table
handles all eight signed/unsigned widths, including zero-extending unsigned int
to long. Common arithmetic types promote small operands to int, select the wider
type, and prefer unsigned when widths match.

Division/remainder use div with a cleared high dividend for unsigned values.
Comparisons use setb/setbe and right shift uses shr instead of signed sar.
Python keeps a readable specifier table with signedness flags instead of C's
bitmask counter. Repeated unsigned is accepted; signed plus unsigned is invalid.

This original commit changes runtime arithmetic but does not yet update the
constant evaluator for unsigned division, comparison or shift. Its existing
historical cast behavior remains. Numeric literal suffixes are still unsupported,
and the port's signed-64-bit literal range diagnostic remains intentional.

## Assembly and WSL example

```sh
printf 'int main(void){return ((unsigned)-1>>1)==2147483647;}\n' > /tmp/lesson131.c
python3 python/main.py /tmp/lesson131.c > /tmp/lesson131.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson131 /tmp/lesson131.s
/tmp/lesson131
echo $?
```

Unsigned -1 has 32 one bits. `shr %cl,%eax` shifts in a zero, producing 2147483647;
the equality returns exit status 1. Tests cover unsigned widths, promotions,
mixed signedness, large division, remainder, casts, return values, exact div/shr/
setb assembly, invalid combinations, execution, and updated original C programs.

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
