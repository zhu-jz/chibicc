# Lesson 37: Octal string escapes

Original chibicc commit: [`699d2b7e3f4ea4ba6ec2d5080f87e243989a5835`](https://github.com/rui314/chibicc/commit/699d2b7e3f4ea4ba6ec2d5080f87e243989a5835).
Earlier explanations are available in Git history.

## What changed

A backslash followed by an octal digit reads up to three digits (0–7) and
produces one byte. `\101` is 65. `\1500` reads only `150`, producing byte 104,
then retains the last 0 as byte 48. Non-octal digits stop the sequence.

The escape helper now returns both decoded bytes and the next source position,
replacing upstream's pointer output parameter with a Python tuple. Values are
masked to eight bits to match storage into C's char buffer. Interior zero bytes
remain in the data and count toward sizeof; the tokenizer also appends the
separate terminating zero.

## Run it

```sh
python3 python/main.py 'int main(){return "\101"[0];}' > /tmp/lesson37.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson37 /tmp/lesson37.s
/tmp/lesson37
echo $?
```

The executable prints nothing; the last command shows **65**. Use an interactive
shell without `set -e` for nonzero statuses. Assembly contains `.byte 65` and
`.byte 0`; the usual char load reads it. No runtime escape processing occurs.

Tests include all upstream octal cases, the three-digit boundary, byte wrapping,
non-octal default escapes, and embedded zeros with correct size. Python's bytes
storage explicitly performs the truncation implicit in upstream's char store.
Hexadecimal escapes are not part of this original commit.

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
