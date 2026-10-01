# Lesson 155: Assemble output unless -S is given

Original chibicc commit: [`140b43358c33fb5e9f86789541dbca306bb64fcc`](https://github.com/rui314/chibicc/commit/140b43358c33fb5e9f86789541dbca306bb64fcc).
Earlier explanations are available in Git history.

## What changed

The driver now writes a temporary assembly file and invokes GNU as to produce an
object file. With -S, assembly itself is the final output. Without -o, it uses the
input basename with .o or .s in the current directory. -S -o - writes assembly
to stdout, and internal -cc1 remains the assembly-generating compiler process.
The driver traces both child commands with -### and propagates their failures.

Python uses a TemporaryDirectory for automatic cleanup and a list of subprocess
arguments instead of C's temporary-file array and fork/exec code. The C-to-assembly
compiler remains our implementation; as assembles that text. GCC is used only
by the examples and tests to link object files. Existing assembly tests now
request -S explicitly so they continue to check the same compiler output.

## Assembly and WSL example

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson155.c
python3 python/main.py -S -o /tmp/lesson155.s /tmp/lesson155.c
python3 python/main.py -o /tmp/lesson155.o /tmp/lesson155.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson155 /tmp/lesson155.o
/tmp/lesson155
echo $?
```

The assembly still places 42 in rax and returns. as turns it into an ELF relocatable
object; GCC links it into an executable, whose shell exit status is 42. Tests
check real object headers and execution, default names, explicit assembly output,
tracing, temporary-file cleanup, assembler errors, and the original fixtures.

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
