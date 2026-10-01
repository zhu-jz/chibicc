# Lesson 146: Default float argument promotion

Original chibicc commit: [`8b14859f63a8389882bdb9330de592a112affa18`](https://github.com/rui314/chibicc/commit/8b14859f63a8389882bdb9330de592a112affa18).
Earlier explanations are available in Git history.

## What changed

When a call runs out of declared parameter types, a float argument now receives
an explicit cast to double. This applies to variadic trailing arguments and to
old-style empty parameter lists. Fixed float parameters still receive float.
The syntax tree records the cast; cvtss2sd performs the conversion at runtime.

Python implements this as one extra parser branch, matching the original C.
This step adds the floating promotion only. The historical caller still leaves
the variadic SSE-register count in al unspecified; promotion itself can be tested
reliably by calling a GCC helper through an old-style declaration and inspecting
the variadic argument tree.

## Assembly and WSL example

```sh
printf 'int add();int main(void){float x=20.5f;return add(x,21.5f);}\n' > /tmp/lesson146.c
printf 'int add(double x,double y){return x+y;}\n' > /tmp/lesson146-helper.c
python3 python/main.py /tmp/lesson146.c > /tmp/lesson146.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson146 /tmp/lesson146.s /tmp/lesson146-helper.c
/tmp/lesson146
echo $?
```

Each float converts to double before being saved and restored into xmm0/xmm1.
The helper returns integer 42, which the shell shows as the executable's exit
status. Tests check omitted, variadic, and fixed parameter types, the conversion
instruction, linked execution, and the original sprintf example.

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
