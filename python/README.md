# Lesson 128: Variadic register save areas

Original chibicc commit: [`754a24fafcea637cab8bc01bb2702069109a0358`](https://github.com/rui314/chibicc/commit/754a24fafcea637cab8bc01bb2702069109a0358).
Earlier explanations are available in Git history.

## What changed

Variadic definitions now reserve a 136-byte local named __va_area__. Its header
stores the fixed integer-argument byte count as gp_offset and a pointer to saved
registers. The prologue saves six general-purpose argument registers and eight
low floating-register slots before the body runs. A user-declared va-list struct
can copy that header and forward integer/pointer arguments to libc vsprintf.

Python loops emit the same saves as upstream's repeated instructions. The helper
area is a local object separate from fixed parameters. This historical step has
no builtin va_start or va_arg syntax: examples copy the exposed header manually.
Overflow stack arguments and a complete floating-point variadic ABI are still
unsupported; the area preserves upstream's layout and zero fp_offset.

## Assembly and WSL example

```sh
printf 'typedef struct V{int gp,fp;void *overflow;void *regs;} V;int f(int x,...){V *v=(V*)__va_area__;char *p=v->regs;return *(int*)(p+v->gp);}int main(){return f(1,42);}\n' > /tmp/lesson128.c
python3 python/main.py /tmp/lesson128.c > /tmp/lesson128.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson128 /tmp/lesson128.s
/tmp/lesson128
echo $?
```

The fixed x consumes rdi, so gp is eight. Saved rsi at that offset contains 42,
which f reads and returns. Tests cover fixed-parameter offsets, reading saved
extras, forwarding to vsprintf, helper area size, separation from parameters,
emitted integer and xmm saves, execution, and the updated function program.

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
