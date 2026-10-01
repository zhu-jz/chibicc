# Lesson 231: Read L-prefixed wide strings

Original chibicc commit: [`cae061af2b65ad0962fb4b6fe3b55abe2f3a5bf8`](https://github.com/rui314/chibicc/commit/cae061af2b65ad0962fb4b6fe3b55abe2f3a5bf8).
Earlier explanations are available in Git history.

L-prefixed strings reuse the UTF-32 reader with signed int elements. On this
x86-64 Linux target, wide strings therefore use four-byte little-endian units
and a four-byte zero terminator. Their payload bytes can match U strings, but
arithmetic and shifts follow signed rather than unsigned integer rules.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){return L"βb"[0]-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

An indexed four-byte load obtains 946; subtraction returns 42. Tests inspect
payload bytes and element signedness, run a signed high-bit shift, preserve
macro stringizing and execute original fixtures. Python passes ty_int into
its existing UTF-32 reader, mirroring the C reuse. This deliberately targets
Linux wide characters; Windows uses a different representation. Wider array
initializer and concatenation paths still retain their earlier limitations.

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
