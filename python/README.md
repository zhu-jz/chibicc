# Lesson 195: Add bundled standard headers

Original chibicc commit: [`7cbfd111d38b70110c9adcdfdae86d07995ae534`](https://github.com/rui314/chibicc/commit/7cbfd111d38b70110c9adcdfdae86d07995ae534).
Earlier explanations are available in Git history.

The historical headers are copied unchanged into include/: float.h, stdalign.h,
stdarg.h, stdbool.h, stddef.h and stdnoreturn.h. They provide floating-point
limits, alignment aliases, the variadic-list layout, boolean aliases, basic
typedefs and NULL, and the noreturn alias. Header guards avoid repeated definitions.

The source compiler already searches python/include beside main.py. The Python
packaging script installs identical header files in include/ beside its .pyz
output, adapting the original stage-two include path to this distribution.
Makefile dependencies rebuild the package when a header changes. The archive
and its sibling include directory are distributed together.

These are the early historical definitions: va_start copies the compiler's
register-save descriptor, va_end expands to nothing, and va_arg is not supplied.
Long-double limits follow this compiler's eight-byte representation. Hexadecimal
floating literals without a decimal point retain the earlier tokenizer limitation.

```sh
printf '#include <stdbool.h>\nint main(void){bool ready=true;return ready+41;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The bool alias becomes _Bool and true becomes 1. Assembly stores the boolean
byte, loads it and adds 41 before returning in %rax. Tests exercise the aliases,
typedefs, size/alignment definitions, floating maxima, va_start with a real
variadic call, repeated inclusion, and packaged header contents and lookup.

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
