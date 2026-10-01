# Lesson 275: Advertise variable-length array support

Original chibicc commit: [`b0109a30c9fa24fedcb4d79bb17788e7ed228636`](https://github.com/rui314/chibicc/commit/b0109a30c9fa24fedcb4d79bb17788e7ed228636).
Earlier explanations are available in Git history.

The compiler now supports variable-length arrays, so it stops predefining
__STDC_NO_VLA__. Headers and conditional compilation can detect that support.
Other predefined feature macros retain their existing values.

```sh
printf '#ifdef __STDC_NO_VLA__\n#error unexpected VLA exclusion\n#endif\nint main(void){int n=2;int x[n];x[1]=42;return x[1];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The preprocessor discards the error branch. Assembly allocates the runtime array,
stores 42 in its second element and returns that element. The feature-macro test
checks this conditional path; predefined macro and VLA tests remain enabled.
Python removes one dictionary entry where C removes one define_macro call.

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
