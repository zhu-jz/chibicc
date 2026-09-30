# Lesson 23: Calls without arguments

Original chibicc commit: [`30a39926272a8341c52018654ca18d2c86ba662b`](https://github.com/rui314/chibicc/commit/30a39926272a8341c52018654ca18d2c86ba662b).
Earlier explanations are available in Git history.

## What changed

An identifier followed by `()` becomes a FUNCALL node rather than a variable
lookup. Calls have integer result type and do not require declarations yet.
Arguments are not accepted in this step.

For `{return ret3();}`, the body contains:

```asm
  mov $0, %rax
  call ret3
  jmp .L.return
```

`call` pushes a return address and transfers execution to the linked function.
Its result arrives in `%rax`. Setting `%rax` to zero supplies the ABI's vector
argument count. The existing epilogue restores the frame and returns from main.

## Run it

```sh
printf 'int ret3(void) { return 3; }\n' > /tmp/helper23.c
python3 python/main.py '{return ret3();}' > /tmp/lesson23.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson23 /tmp/lesson23.s /tmp/helper23.c
/tmp/lesson23
echo $?
```

The executable prints nothing; the last command displays exit status **3**.
Use an interactive shell without `set -e` for nonzero example statuses.
GCC compiles only the test helper and assembles/links the Python output.

Tests include upstream's ret3/ret5 examples, calls in arithmetic, AST/result
types, the emitted call sequence, and rejection of arguments. As in upstream,
this step does not adjust alignment for calls inside temporary expressions;
its trivial helper functions do not require an aligned stack. Unknown function
names produce assembly but fail when linking unless a definition is supplied.
All local slots are still eight bytes, and numeric tokens are checked to fit
0 through 2147483647. No new Python/C behavioral differences are introduced.

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
