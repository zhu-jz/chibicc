# Lesson 125: Stack alignment around calls

Original chibicc commit: [`6a0ed71107670b404af04bc20a2461165483f390`](https://github.com/rui314/chibicc/commit/6a0ed71107670b404af04bc20a2461165483f390).
Earlier explanations are available in Git history.

## What changed

Calls now account for temporary expression pushes. Function stack frames already
start on a 16-byte boundary; each pushed temporary changes rsp by eight bytes.
After moving arguments into registers, an odd temporary depth triggers `sub $8`
before call and `add $8` afterward. An even depth requires no padding.

Python uses the existing integer depth counter as upstream does. The padding is
not an expression value, so it does not alter that counter. The x86-64 System V
ABI requires rsp aligned to 16 before call; the pushed return address means the
callee sees rsp modulo 16 equal to eight on entry.

## Assembly and WSL example

```sh
printf 'int f(void){return 41;}int main(){return f()+1;}\n' > /tmp/lesson125.c
python3 python/main.py /tmp/lesson125.c > /tmp/lesson125.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson125 /tmp/lesson125.s
/tmp/lesson125
echo $?
```

The emitter evaluates the right operand 1 first and pushes it. It pads the stack
by eight bytes around call f, restores that padding, pops the operand, and adds.
Exit status is 42. Tests use a tiny GCC-compiled naked assembly helper to inspect
actual callee-entry rsp, covering direct calls, odd-depth binary/assignment calls,
nested argument calls, emitted padding, and all original C examples.

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
