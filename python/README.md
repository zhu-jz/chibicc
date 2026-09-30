# Lesson 36: Named string escapes

Original chibicc commit: [`ad7749f2fad87a4b1df644d4e1c345b3f87d386d`](https://github.com/rui314/chibicc/commit/ad7749f2fad87a4b1df644d4e1c345b3f87d386d).
Earlier explanations are available in Git history.

## What changed

The tokenizer first finds the closing quote while skipping escaped characters,
then decodes the contents. This separates source spelling from stored bytes.
The recognized escapes are `\a`, `\b`, `\t`, `\n`, `\v`, `\f`, `\r`, and GNU
`\e` (byte 27). Escaped quotes and backslashes work through the default rule:
an unrecognized escape contributes its character without the backslash.

`"\ax\ny"` becomes bytes 7, 120, 10, 121, 0. Its sizeof is 5 even though its
source spelling is longer. Python uses bytearray while decoding, then stores
immutable bytes including the terminating zero. Named codes come from Python's
own byte escapes, paralleling upstream's use of its host C compiler's escapes.

## Run it

```sh
python3 python/main.py 'int main(){return "\n"[0];}' > /tmp/lesson36.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson36 /tmp/lesson36.s
/tmp/lesson36
echo $?
```

The executable prints nothing; the last command shows **10**. Use an interactive
shell without `set -e` for nonzero statuses. Assembly emits `.byte 10` and
`.byte 0`, then indexes and loads the byte. Escape handling is entirely in the
tokenizer; no code-generator changes are needed.

Tests cover every new upstream named/default escape and mixed-string position,
escaped quotes/backslashes, decoded size, and an incomplete escape at EOF.
The port reports incomplete strings cleanly rather than permitting a C read
past the input buffer. Diagnostics for unclosed strings now point just after
the opening quote, matching this original refactor. Numeric escape decoding
is not part of this commit.

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
