# Lesson 157: Link executables unless -c is given

Original chibicc commit: [`8b726b54893e11427533fcceb7206b97c25f50a6`](https://github.com/rui314/chibicc/commit/8b726b54893e11427533fcceb7206b97c25f50a6).
Earlier explanations are available in Git history.

## What changed

The driver now compiles and assembles C inputs into temporary objects, then runs
GNU ld to create an executable. -c stops at object files; -S stops at assembly.
Normal linking accepts multiple sources and existing .o inputs, with a single -o
for the final executable or a.out by default. The driver rejects unknown suffixes.

The linker command supplies x86-64 startup objects, the dynamic loader, library
search paths, libc, and GCC runtime libraries. Python uses glob and Path to find
them with the original search order; it invokes ld directly and never asks GCC
to compile C. Temporary objects live until linking completes and are then removed.
The historical .s branch assembles a file but does not add it to the link inputs;
.o inputs retain the original branch behavior even with stopping flags.

## Assembly and WSL example

```sh
printf 'int f(void);int main(void){return f();}\n' > /tmp/lesson157-main.c
printf 'int f(void){return 42;}\n' > /tmp/lesson157-answer.c
python3 python/main.py -### -o /tmp/lesson157 /tmp/lesson157-main.c /tmp/lesson157-answer.c
/tmp/lesson157
echo $?
python3 python/main.py -S -o /tmp/lesson157.s /tmp/lesson157-main.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson157-gcc /tmp/lesson157.s /tmp/lesson157-answer.c
/tmp/lesson157-gcc
echo $?
```

The trace shows the compiler children, as, and ld. Linking resolves f's function
address; main calls it and exits with 42. The later commands demonstrate linking
the emitted assembly with GCC as well. Tests check executable/object ELF types, multiple sources,
existing objects, a.out, dynamic libc calls, suffix errors, assembly, and upstream.

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
