# Lesson 253: Name variadic macro parameters

Original chibicc commit: [`007e526ec50bde4b366d0927ad20d9cd4ac53abf`](https://github.com/rui314/chibicc/commit/007e526ec50bde4b366d0927ad20d9cd4ac53abf).
Earlier explanations are available in Git history.

GNU macro definitions can now name their variadic tail, as in `args...`.
Each macro records that name rather than a boolean variadic flag, and invocation
collects the remaining comma-separated tokens under it. GNU comma removal also
recognizes the chosen variadic name.

```sh
printf '#define SUM(x,args...) x+args\nint main(void){return SUM(12,30);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Substitution produces `12+30`; the ordinary addition assembly returns 42.
Tests cover an empty tail, only a variadic parameter, fixed parameters before it,
multi-argument calls, comma removal and the original macro.c additions.
Python passes the variadic name alongside its argument dictionary instead of
adding C's is_va_args flag to each linked argument node. The earlier __VA_OPT__
helper still checks the literal name __VA_ARGS__, just as in this original
commit, so it does not recognize a GNU tail named args. That limit is tested.

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
