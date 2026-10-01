# Lesson 147: Variadic floating parameter offsets

Original chibicc commit: [`e452cf721511dbf0d7f8c8f469f2dd67d8a5ee93`](https://github.com/rui314/chibicc/commit/e452cf721511dbf0d7f8c8f469f2dd67d8a5ee93).
Earlier explanations are available in Git history.

## What changed

A variadic function now counts its fixed integer and floating parameters separately.
Its saved argument header starts gp_offset at eight times the integer count and
fp_offset at 48 plus eight times the floating count. The first six saved integer
registers occupy 48 bytes; floating register slots follow them.

Python counts the parameter list directly, matching the original linked-list loop.
This historical save area uses eight-byte floating slots rather than the full
sixteen-byte System V slots. The tests check that actual layout and the original
single-floating-argument forwarding example. This change concerns the callee's
header; the caller's al bookkeeping remains incomplete in the original commit.

## Assembly and WSL example

```sh
printf 'typedef struct V{int gp;int fp;void *overflow;void *regs;} V;int f(double x,...){V *v=(V*)__va_area__;return *(double*)((char*)v->regs+v->fp);}int main(void){return f(1.0,42.0);}\n' > /tmp/lesson147.c
python3 python/main.py /tmp/lesson147.c > /tmp/lesson147.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson147 /tmp/lesson147.s
/tmp/lesson147
echo $?
```

The prologue saves xmm0 and xmm1 and writes fp_offset=56. Adding that offset to
regs finds the first trailing double, 42.0. Conversion to int produces shell exit
status 42. Tests cover mixed fixed parameters, trailing integers and doubles,
calls from GCC, header instructions, execution, and original forwarding code.

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
