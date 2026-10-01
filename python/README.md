# Lesson 150: Build and test a packaged compiler

Original chibicc commit: [`5d15431df1abab3a5cf596fabe0a77c030a10791`](https://github.com/rui314/chibicc/commit/5d15431df1abab3a5cf596fabe0a77c030a10791).
Earlier explanations are available in Git history.

## What changed

The original commit adds a stage-two C compiler built by compiling chibicc with
itself, then runs the same tests and driver checks against both builds. Our Python
compiler emits C-program assembly and cannot compile its own Python source.
The intentional Python adaptation builds a standalone .pyz archive with zipapp
and runs the same suite against the source compiler and the packaged compiler.
This is packaging validation, not a claim of self-hosting.

build.py copies the current compiler modules and MIT notice, and writes a small
entry point that preserves compiler exit statuses. test.py accepts --compiler
so its existing command-line, assembly, and execution tests exercise either
entry point. python/Makefile provides test, test-stage2, and test-all. The build
uses Python's standard library and never invokes the original C compiler.

## Assembly and WSL example

```sh
python3 python/build.py
printf 'int main(void){return 42;}\n' > /tmp/lesson150.c
python3 python/build/chibicc.pyz /tmp/lesson150.c > /tmp/lesson150.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson150 /tmp/lesson150.s
/tmp/lesson150
echo $?
make -C python test-all
```

The archive emits the same mov $42, %rax and return sequence as the source
entry point. GCC links it and the shell shows exit status 42. test-all runs the
full suite twice. Build tests also check help and compilation-error exit status;
build output is ignored by Git and the source files remain under python/.

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
