# Lesson 140: Floating locals and casts

Original chibicc commit: [`29de46aed47e5308db9a0aef6e13610dea8fb389`](https://github.com/rui314/chibicc/commit/29de46aed47e5308db9a0aef6e13610dea8fb389).
Earlier explanations are available in Git history.

## What changed

float and double become declaration keywords. Local floating values load/store
through xmm0 using movss or movsd. The cast matrix grows to ten types, using
cvtsi2ss/cvtsi2sd for integer-to-floating conversion and cvttss2si/cvttsd2si for
truncating floating-to-integer conversion. Float/double conversion uses cvtss2sd
or cvtsd2ss. Assignment and return casts reuse that matrix automatically.

Python splits multi-instruction cast entries into assembly lines instead of C's
semicolon-separated strings. The unsigned-long-to-double path handles values
with the top bit set by halving and then doubling the converted value. The
historical unsigned-long-to-float path still uses signed conversion. Out-of-range
floating-to-integer behavior follows the emitted SSE instructions; full C
semantics for such conversions are not newly promised.

This commit adds local storage and casts. Floating arithmetic, general condition
checks, global floating initializers and floating argument-register handling
remain incomplete. Long double declarations are not supported; literal L still
selects double as introduced in lesson 139.

## Assembly and WSL example

```sh
printf 'int main(void){double x=42.9;float y=x;return (int)y;}\n' > /tmp/lesson140.c
python3 python/main.py /tmp/lesson140.c > /tmp/lesson140.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson140 /tmp/lesson140.s
/tmp/lesson140
echo $?
```

Assembly stores x with movsd, converts it with cvtsd2ss and stores y with movss.
cvttss2sil truncates y toward zero for the return, giving exit status 42. Tests
cover local scalars and arrays, both floating widths, signed/unsigned integer
casts, narrowing, exact SSE load/store/conversion instructions, execution, and
original cast/float/sizeof programs.

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
