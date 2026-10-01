# Lesson 136: Recognizing ignored declaration qualifiers

Original chibicc commit: [`b77355427575385b6f0b6c0a914600b79b4e4412`](https://github.com/rui314/chibicc/commit/b77355427575385b6f0b6c0a914600b79b4e4412).
Earlier explanations are available in Git history.

## What changed

The parser recognizes const, volatile, auto, register, restrict, __restrict,
__restrict__, and _Noreturn, then intentionally ignores them. Declaration
specifiers accept all of these; qualifiers immediately after pointer stars accept
const, volatile and restrict spellings. A shared pointers routine handles named
and abstract declarators.

This is syntax compatibility, as in upstream: const does not prevent assignment,
volatile does not change memory operations, and _Noreturn does not change control
flow. Python uses the same keyword sets and simple loops. Qualifier-only
specifiers retain the compiler's historical default-int behavior.

## Assembly and WSL example

```sh
printf 'int main(void){const volatile int x=42;int *const p=&x;return *p;}\n' > /tmp/lesson136.c
python3 python/main.py /tmp/lesson136.c > /tmp/lesson136.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson136 /tmp/lesson136.s
/tmp/lesson136
echo $?
```

The qualifiers produce no instructions. Assembly initializes x and p, follows
the pointer, and returns exit status 42. Tests cover declaration and pointer
qualifiers, abstract casts, intentionally writable const objects, identical
assembly with/without qualifiers, execution, and new original const/compat code.

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
