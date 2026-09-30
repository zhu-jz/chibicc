# Lesson 87: Array parameters become pointers

Original chibicc commit: [`79632219d0991aae83e1de3c56df7d664205c2b6`](https://github.com/rui314/chibicc/commit/79632219d0991aae83e1de3c56df7d664205c2b6).
Earlier explanations are available in Git history.

## What changed

In a function parameter list, an array declaration adjusts to a pointer to its
element type. int x[] and int x[3] both describe int *x, and int *x[] becomes
int **x. Only the outer array layer adjusts: int x[][3] becomes a pointer to an
array of three ints, so row indexing still scales by twelve bytes. The parameter
name is preserved for creating its local stack slot.

Python checks the type kind after parsing the declarator and replaces it with
a named pointer type, just as the C commit does. Ordinary local arrays keep their
array types and sizes; this adjustment is specific to parameters.

## Assembly and WSL example

```sh
printf 'int f(int x[]){return x[1];}int main(){int a[2];a[1]=42;return f(a);}\n' > /tmp/lesson87.c
python3 python/main.py /tmp/lesson87.c > /tmp/lesson87.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson87 /tmp/lesson87.s
/tmp/lesson87
echo $?
```

The caller passes a's address in rdi. f saves that eight-byte pointer, scales its
index by four, and loads a[1]. The shell displays 42. Tests cover incomplete and
sized parameter arrays, multidimensional arrays, arrays of pointers, sizeof and
name metadata, pointer-width stores, and updated original function tests.

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
