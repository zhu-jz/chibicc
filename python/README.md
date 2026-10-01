# Lesson 149: Long double as a double alias

Original chibicc commit: [`9bf96124ba1e0cb95f491bd0c91d4e9c7a9850da`](https://github.com/rui314/chibicc/commit/9bf96124ba1e0cb95f491bd0c91d4e9c7a9850da).
Earlier explanations are available in Git history.

## What changed

The declaration-specifier table now accepts one long together with double and
selects the existing DOUBLE type. Both long double and double long therefore
have size and alignment eight and use the ordinary double instructions and ABI.
Repeated long in long long double remains invalid.

This is the original compiler's deliberate historical simplification, not GCC's
x86-64 long-double format. Python adds one readable table entry; no new numeric
representation or code-generation path is required.

## Assembly and WSL example

```sh
printf 'long double x=42.0L;int main(void){return x;}\n' > /tmp/lesson149.c
python3 python/main.py /tmp/lesson149.c > /tmp/lesson149.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson149 /tmp/lesson149.s
/tmp/lesson149
echo $?
```

The global holds an eight-byte double. movsd loads it into xmm0, and cvttsd2sil
converts it to main's integer return value. The shell displays exit status 42.
Tests check size/alignment, both specifier orders, globals, function parameters,
invalid repetition, real execution, and the original sizeof fixture.

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
