# Lesson 154: Separate the driver and compiler process

Original chibicc commit: [`f3d96136f292dea83fd760098d189a6884f59eb0`](https://github.com/rui314/chibicc/commit/f3d96136f292dea83fd760098d189a6884f59eb0).
Earlier explanations are available in Git history.

## What changed

The normal entry point now launches a child invocation of the same Python compiler
with -cc1. That internal mode reads, tokenizes, parses, and generates assembly.
The driver inherits stdin/stdout/stderr for the child, waits for it, and reports
success or failure. -### prints the child command to stderr while still running it.
It is a trace option at this historical point, not a dry run.

Python's subprocess.run replaces the C fork/exec/wait sequence. It invokes the
same Python source or archive entry point, never the original C compiler. Child
errors retain their diagnostics and become driver status 1; launch failures
receive a readable error. Compilation and emitted assembly are unchanged.

## Assembly and WSL example

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson154.c
python3 python/main.py -### /tmp/lesson154.c > /tmp/lesson154.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson154 /tmp/lesson154.s
/tmp/lesson154
echo $?
```

The displayed child command includes -cc1. Its assembly still places 42 in rax
and returns through main's epilogue, so the shell displays exit status 42. Tests
compare driver and direct -cc1 assembly, verify tracing and failure propagation,
exercise output files and stdin, run the packaged compiler, and execute upstream.

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
