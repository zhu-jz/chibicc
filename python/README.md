# Lesson 38: Hexadecimal string escapes

Original chibicc commit: [`c2cc1d3c4500caa34da5e68eb62b7474caf96fe2`](https://github.com/rui314/chibicc/commit/c2cc1d3c4500caa34da5e68eb62b7474caf96fe2).
Earlier explanations are available in Git history.

## What changed

`\x` requires at least one hexadecimal digit and consumes all consecutive
hexadecimal digits. Both letter cases are accepted. `\x00ff` produces one byte
255, while `\x41Z` produces byte 65 followed by Z. This differs from the
three-digit maximum for octal escapes.

The tokenizer uses standard-library `string.hexdigits` and `int(digit,16)`
instead of C's isxdigit and a manual digit helper. It reports an invalid escape
at the first character after x if no digits follow. Decoded values are masked
to eight bits before storing. Python's accumulator does not overflow a signed
C int, so long sequences have defined final-byte truncation in this port.

## Run it

```sh
python3 python/main.py 'int main(){return "\x77"[0];}' > /tmp/lesson38.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson38 /tmp/lesson38.s
/tmp/lesson38
echo $?
```

The executable prints nothing; the last command shows **119**. Use an interactive
shell without `set -e` for nonzero statuses. Assembly stores `.byte 119` plus
its terminator and performs the normal signed byte load. Tests cover every
upstream hex example, mixed case, stopping at a non-hex character, decoded
size, truncation, invalid empty sequences, and earlier escape forms.

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
