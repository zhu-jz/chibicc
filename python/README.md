# Lesson 260: Give inline functions internal linkage by default

Original chibicc commit: [`31087f8d4bbc06e5bec44cb14cab3a922b5e4855`](https://github.com/rui314/chibicc/commit/31087f8d4bbc06e5bec44cb14cab3a922b5e4855).
Earlier explanations are available in Git history.

Function declarations now record inline. An inline function becomes static
unless it also has extern; extern inline emits an externally visible function.
This allows repeated inline definitions in separate translation units without
duplicate global symbols. The compiler still emits normal calls and bodies.

```sh
printf 'inline int f(void){return 42;}int main(void){return f();}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly gives f local linkage, generates its ordinary frame and return, then
calls it from main. No machine-code inlining happens at this stage. Tests inspect
function flags and symbols, link two files with repeated inline names, link an
extern inline definition from another file, and run the original fixtures.
Python adds boolean fields to declaration attributes and function objects;
C adds matching struct fields. Storage-class diagnostic wording now includes
inline, with the original validation condition preserved.

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
