# Lesson 137: Ignored keywords in array dimensions

Original chibicc commit: [`93d12771d009924fb598b088dc4bd9b67fd9a09a`](https://github.com/rui314/chibicc/commit/93d12771d009924fb598b088dc4bd9b67fd9a09a).
Earlier explanations are available in Git history.

## What changed

Array dimension parsing now skips repeated static and restrict before a bound.
This accepts parameter spelling such as `int a[restrict static 3]`; its array
type still adjusts to an int pointer as before. The keywords impose no minimum
length checks or extra runtime behavior in this historical compiler.

The original title mentions const, but its actual diff handles static and
restrict only. Python follows that diff, so `[const 3]` remains rejected. Existing
type/declaration qualifier support does not automatically apply inside brackets.

## Assembly and WSL example

```sh
printf 'int f(int a[restrict static 3]){return a[2];}int main(void){int a[3]={1,2,42};return f(a);}\n' > /tmp/lesson137.c
python3 python/main.py /tmp/lesson137.c > /tmp/lesson137.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson137 /tmp/lesson137.s
/tmp/lesson137
echo $?
```

The caller passes the array address in rdi. f stores that pointer, adds eight
bytes for index two, and returns 42. Tests check accepted keyword order,
parameter pointer adjustment, emitted register storage, the actual const
limitation, execution, and the original compatibility program.

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
