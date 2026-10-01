# Lesson 209: Undefine macros from command-line options

Original chibicc commit: [`be8b6f6d31f0c73c2aabffdf2794f20c69567cdb`](https://github.com/rui314/chibicc/commit/be8b6f6d31f0c73c2aabffdf2794f20c69567cdb).
Earlier explanations are available in Git history.

-Uname and -U name remove a macro definition, including predefined names.
-D and -U act in their original command-line order. Source directives then
run normally, so a later #define can restore the name. #undef and -U now
share one helper. Removing an unknown name is harmless.

```sh
printf '#ifdef FLAG\n#error flag still defined\n#endif\nint main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -DFLAG -UFLAG -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The skipped #error contributes no assembly. Main still returns the immediate
42 through rax. Tests exercise option forms and ordering, repeated removal,
predefined names, later source definitions and original fixtures. Python removes
the dictionary entry where C adds a deleted linked-list entry; expansion sees
the same result. Missing separate -U arguments receive a usage error.

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
