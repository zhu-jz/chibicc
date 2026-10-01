# Lesson 130: Signed integer type spellings

Original chibicc commit: [`3f59ce79554fcbccd15d42ff4b4ddb91812c7045`](https://github.com/rui314/chibicc/commit/3f59ce79554fcbccd15d42ff4b4ddb91812c7045).
Earlier explanations are available in Git history.

## What changed

`signed` now qualifies char, short, int, long, or long long. Used alone it means
int. These types already had signed arithmetic and loads, so the change adds
spellings rather than new code-generation behavior. Keyword order remains
flexible; repeated signed is accepted because upstream tracks it as a flag.

Python keeps a boolean alongside the readable type-specifier combination table,
rather than C's bitmask counter. Invalid combinations such as signed void and
signed _Bool still fail. Long long remains the same eight-byte type as long.

## Assembly and WSL example

```sh
printf 'int main(void){signed char x=255;return x<0;}\n' > /tmp/lesson130.c
python3 python/main.py /tmp/lesson130.c > /tmp/lesson130.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson130 /tmp/lesson130.s
/tmp/lesson130
echo $?
```

The store keeps low byte ff; `movsbl` loads it as -1. The comparison returns true,
giving exit status 1. Tests cover aliases, keyword order, repeated signed, sizes,
signed-char execution and assembly, rejected types, and original sizeof examples.

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
