# Lesson 35: Formatting utility refactor

Original chibicc commit: [`35a0bcd366163168bf3337975130f62fc1c30235`](https://github.com/rui314/chibicc/commit/35a0bcd366163168bf3337975130f62fc1c30235).
Earlier explanations are available in Git history.

## What changed

Upstream adds a printf-style `format()` utility implemented with a memory
stream, and uses it to generate anonymous names instead of writing into a
fixed-size C buffer. It introduces no language or assembly change.

The Python port already uses `f".L..{self.unique_id}"`, which constructs a
string of the required length directly. We retain that straightforward
standard-language operation. An extra utility wrapping it would add no value.
This is an intentional Python/C implementation difference: Python does not
need C allocation, varargs, or stream management to format a name.

Each literal still gets a distinct global name, byte data, and a RIP-relative
address. The existing string tests and a two-literal name/data check verify
that behavior. The compiler files and generated assembly remain unchanged.

## Run it

```sh
python3 python/main.py 'int main(){return "abc"[1];}' > /tmp/lesson35.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson35 /tmp/lesson35.s
/tmp/lesson35
echo $?
```

The executable prints nothing; the last command shows **98**. Use an interactive
shell without `set -e` for nonzero statuses. The assembly retains `.byte` data,
`lea .L..0(%rip),%rax`, a byte-offset calculation, and a signed char load.
String escapes remain unsupported at this exact stage.

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
