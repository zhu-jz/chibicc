# Lesson 86: Incomplete array types

Original chibicc commit: [`29ed294906ebc271c32a755e1aefc360df4d3863`](https://github.com/rui314/chibicc/commit/29ed294906ebc271c32a755e1aefc360df4d3863).
Earlier explanations are available in Git history.

## What changed

An empty [] creates an incomplete array type with length -1 and negative size.
A pointer to that type is still complete and eight bytes wide. Recursive suffix
parsing handles a pointer such as int(*)[][10]. Local object declarations reject
negative-sized types because stack storage needs a known size. The Member model
also gains a token field for diagnostics, matching the original structural change.

Python uses the same negative sentinel rather than a separate incomplete flag.
This commit does not complete arrays from initializers or fully diagnose global
incomplete definitions/sizeof on incomplete types; those historical limits remain.

## Assembly and WSL example

```sh
printf 'int main(){return sizeof(int(*)[][10]);}\n' > /tmp/lesson86.c
python3 python/main.py /tmp/lesson86.c > /tmp/lesson86.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson86 /tmp/lesson86.s
/tmp/lesson86
echo $?
```

sizeof measures the pointer, so the emitter uses `mov $8, %rax` without allocating
or accessing the incomplete array. The shell displays 8. Tests inspect nested
type metadata, dereference a pointer to an incomplete array with a known valid
object, check local errors and assembly, and run updated original sizeof tests.

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
