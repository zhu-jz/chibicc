# Lesson 115: Global alignment directives

Original chibicc commit: [`157356c769d777b1721da8218724608081137fe2`](https://github.com/rui314/chibicc/commit/157356c769d777b1721da8218724608081137fe2).
Earlier explanations are available in Git history.

## What changed

The data emitter now writes `.align N` for each global object's type alignment.
Consecutive objects within a section can therefore receive padding before
naturally aligned int, long, pointer, and aggregate storage. Local alignment was
already handled while assigning stack offsets.

Python emits the same byte-based GNU assembler directive as upstream. The exact
historical ordering places .align before the section directive; when switching
between .data and .bss it consequently aligns the previously selected section.
This commit does not yet fix that ordering. Tests check directives and actual
addresses for consecutive objects within one section.

## Assembly and WSL example

```sh
printf 'long g=42;char pad=1;int main(){return g;}\n' > /tmp/lesson115.c
python3 python/main.py /tmp/lesson115.c > /tmp/lesson115.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson115 /tmp/lesson115.s
/tmp/lesson115
echo $?
```

The emitter's global order places pad first, then `.align 8` before g, adding
padding in .data. Main loads g and returns exit status 42. Tests verify byte
alignment directives for all scalar widths, real global addresses in .data and
.bss, section expectations, execution, and all original C examples.

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
