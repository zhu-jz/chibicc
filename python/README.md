# Lesson 76: Declarations in for loops

Original chibicc commit: [`a4fea2ba3edeb8ab5a0812a09f14c2a771aa196c`](https://github.com/rui314/chibicc/commit/a4fea2ba3edeb8ab5a0812a09f14c2a771aa196c).
Earlier explanations are available in Git history.

## What changed

A for initializer can now be a declaration, such as `for(int i=0;...)`. Parsing
enters a scope before the initializer and leaves it after the body. The variable
is visible in the condition, increment, and body, then disappears; an outer
variable with the same name becomes visible again. The generated loop structure
is unchanged because a declaration already becomes a block of assignments.

As in the original, storage class specifiers in this initializer are rejected.
Python keeps loop scopes on the same explicit scope stack used by ordinary
blocks. Stack storage remains allocated once in the function prologue.

## Assembly and WSL example

```sh
printf 'int main(){int sum=0;for(int i=0;i<=10;i=i+1)sum=sum+i;return sum;}\n' > /tmp/lesson76.c
python3 python/main.py /tmp/lesson76.c > /tmp/lesson76.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson76 /tmp/lesson76.s
/tmp/lesson76
echo $?
```

The initializer stores zero to i's stack slot; the begin label tests i, the body
updates sum, and the increment runs before jumping back. The program exits with
55. Tests cover sums, nested loops and shadowing, visibility after the loop,
assembly initialization, diagnostics, and the updated original control tests.

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
