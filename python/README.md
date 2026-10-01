# Lesson 188: Add predefined macros

Original chibicc commit: [`5f5a8507ff2f2509c27ac1a196fd1874345e5e95`](https://github.com/rui314/chibicc/commit/5f5a8507ff2f2509c27ac1a196fd1874345e5e95).
Earlier explanations are available in Git history.

Preprocessing initializes the original set of 41 built-in object-like macros.
They identify the x86-64 Linux target, describe C type sizes and language
assumptions, and supply a few alternate keyword spellings. They are ordinary
macro definitions afterward: source can redefine or undefine them.

Each Python compilation constructs a fresh dictionary, preventing changes from
leaking into the next compilation. Built-in replacement tokens have a synthetic
`<built-in>` source file, matching C. Values follow this historical compiler,
not the host Python process or GCC: long double is still eight bytes, and some
provided keyword aliases refer to syntax not implemented at this stage.

```sh
printf '#if __STDC__ && defined(__x86_64__)\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The target condition selects main; assembly loads 42 into `%rax` and returns.
Tests check target conditions, type-size agreement, the unsigned size type,
empty label prefix, the alignment alias, redefinition and reset between calls.
The original fixture's new __STDC__ assertion runs unchanged.

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
