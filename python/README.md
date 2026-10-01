# Lesson 165: Add #else

Original chibicc commit: [`c6e81d22f8189cd7bfcfcc33e4ac462529418192`](https://github.com/rui314/chibicc/commit/c6e81d22f8189cd7bfcfcc33e4ac462529418192).
Earlier explanations are available in Git history.

`#else` selects the second branch when its `#if` expression was zero. Each
conditional now records its opening token, whether the first branch was
included, and whether an `#else` has appeared. A Python dataclass replaces the
C linked stack entry; a list supplies the stack.

Skipping nested blocks uses a second helper that passes their entire matching
`#endif`, so inner `#else` directives cannot stop an outer skip. Stray and
repeated `#else` directives are errors. The prior extra-token warning behavior
is retained.

```sh
printf '#if 0\ninvalid\n#else\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The chosen branch produces ordinary function assembly: load 42 into `%rax`,
restore the stack frame and return. Neither the discarded branch nor the
conditional directives produce instructions. Tests run both branch choices,
nested alternatives, missing includes in discarded branches and diagnostics.

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
