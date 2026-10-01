# Lesson 101: Infer array lengths from initializers

Original chibicc commit: [`5b955336032881edf835a50fb63f9581af1efd73`](https://github.com/rui314/chibicc/commit/5b955336032881edf835a50fb63f9581af1efd73).
Earlier explanations are available in Git history.

## What changed

An incomplete outer array type may now be completed by its initializer. Strings
supply their byte length including the terminator. For a brace list, the parser
first counts outer elements using a dummy initializer, then allocates a complete
initializer tree and parses the list again. Only the real tree emits assignments,
so side effects still execute once. Inner array dimensions must remain complete.

The variable receives the initializer's completed type before clearing/assignment
lowering and stack allocation. An incomplete-array typedef stays unchanged, so
two variables using it can infer different lengths. Declarations check for a
still-incomplete object after processing an optional initializer.

Python returns the initializer and token index, then sets var.ty; C uses an
additional Type** output parameter. Replacing the initializer's fields mirrors
the original struct copy. The two parsing passes can allocate compiler temporaries
in both passes, matching the original; they do not execute source expressions.

## Assembly and WSL example

```sh
printf 'int main(){int a[]={1,2,42};return a[2];}\n' > /tmp/lesson101.c
python3 python/main.py /tmp/lesson101.c > /tmp/lesson101.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson101 /tmp/lesson101.s
/tmp/lesson101
echo $?
```

The inferred array is twelve bytes. Its clearing uses `mov $12, %rcx`, followed
by element stores; the final scaled load returns 42. The shell displays 42.
Tests cover numeric/string inference, independent typedef uses, multidimensional
arrays, once-only runtime effects, type metadata, assembly size, missing
initializers, and the updated original initializer program.

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
