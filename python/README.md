# Lesson 262: Describe diagnostic and output formatting contracts

Original chibicc commit: [`6a2dc5a48a75b65aa2e3f606d195ef0fef3c4442`](https://github.com/rui314/chibicc/commit/6a2dc5a48a75b65aa2e3f606d195ef0fef3c4442).
Earlier explanations are available in Git history.

This original commit adds GCC printf-format attributes to the C compiler's own
formatting helpers. GCC can then report mismatched printf arguments while
building the compiler. It adds no new syntax to programs compiled by chibicc;
in particular, parsing __attribute__ is not introduced here.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The assembly still loads and returns 42. The Python port already constructs
assembly and diagnostics with strings and f-strings rather than a variadic
printf helper. This step adds explicit message/return annotations to diagnostic
interfaces and checks syntax with `make -C python check`; existing diagnostic,
Unicode-caret and emitted-assembly tests verify the formatting behavior.
Python annotations document the contract but py_compile does not perform static
type checking. They do not claim GCC's format-attribute enforcement. The C
conditional attribute macro and its fallback have no Python runtime equivalent.

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
