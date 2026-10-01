# Lesson 179: Use the Python preprocessor for every upstream test

Original chibicc commit: [`769b5a0941694ccdcfe61528053c3d93cb53de80`](https://github.com/rui314/chibicc/commit/769b5a0941694ccdcfe61528053c3d93cb53de80).
Earlier explanations are available in Git history.

Every upstream C test now enters the Python compiler as its original source
file. The test runner no longer asks GCC to preprocess ordinary fixtures first.
Includes, ASSERT parameter substitution and stringizing all run through our
own preprocessor. The original macro test switches to the shared test header.

This original commit changes the build/test workflow rather than the compiler
algorithm. Python applies the same change to its unittest fixture runner;
its packaged entry point uses that same runner. GCC assembles and links the
emitted assembly with the unchanged C support helper. The helper supplies
runtime assertions and is not the original compiler.

```sh
printf '#include "%s/python/test/test.h"\nint main(void){ASSERT(42,6*7);return 42;}\n' "$PWD" > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s -xc python/test/common
/tmp/lesson
echo $?  # 42
```

ASSERT becomes a call with the expected value, actual expression and a generated
string. Assembly multiplies 6 by 7 and passes arguments to the assertion helper,
then returns 42 in `%rax`. All upstream programs are assembled, linked and run
through both the source and packaged Python compiler entry points.

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
