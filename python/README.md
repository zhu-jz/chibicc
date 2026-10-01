# Lesson 251: Omit commas before empty GNU variadic arguments

Original chibicc commit: [`083c27559e5d8fce9c3b588fc4c01769ca9dd10d`](https://github.com/rui314/chibicc/commit/083c27559e5d8fce9c3b588fc4c01769ca9dd10d).
Earlier explanations are available in Git history.

The GNU `,##__VA_ARGS__` extension now removes all three tokens when the raw
variadic argument list is empty. With nonempty arguments it keeps the comma
and expands the argument normally, bypassing ordinary token pasting.
The special case applies only to the variadic parameter name.

```sh
printf '#define CALL(f,x,...) f(x,##__VA_ARGS__)\nint f(int x){return x;}int main(void){return CALL(f,42);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The expansion is `f(42)` with no trailing comma. Assembly passes 42 in the first
integer argument register, calls f and returns its value. Tests inspect empty,
explicitly empty and multi-argument expansions, run both call forms, retain
ordinary named-parameter pasting, and execute the original sprintf fixtures.
Python advances a token-list index where C advances linked pointers. Like the
original step, empty detection occurs before argument macro expansion.

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
