# Lesson 152: Function parameter adjustment

Original chibicc commit: [`c5953ba1328fa86f906406843eb9f23cd596ef04`](https://github.com/rui314/chibicc/commit/c5953ba1328fa86f906406843eb9f23cd596ef04).
Earlier explanations are available in Git history.

## What changed

A parameter declared with function type now becomes a pointer to that function.
For example, int apply(int fn(int), int x) stores fn as an eight-byte pointer and
calls it indirectly. This adjustment happens only in the parameter context;
function declarations themselves keep their function type.

Python extends the existing array-parameter adjustment and preserves both name
and name_pos. Retaining name_pos gives a readable missing-name error for unnamed
parameters in definitions instead of a null diagnostic-token failure. Pointer
argument passing and indirect calls already exist from the preceding lesson.

## Assembly and WSL example

```sh
printf 'int f(int x){return x+1;}int apply(int fn(int),int x){return fn(x);}int main(void){return apply(f,41);}\n' > /tmp/lesson152.c
python3 python/main.py /tmp/lesson152.c > /tmp/lesson152.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson152 /tmp/lesson152.s
/tmp/lesson152
echo $?
```

Main passes f's address in rdi and 41 in esi. apply saves fn as a pointer, loads
it into rax, and calls it with 41 in edi. The final return value is 42, visible
as the shell exit status. Tests cover callbacks, adjusted type size and metadata,
typedef prototypes, missing names, prologue instructions, execution, and upstream.

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
