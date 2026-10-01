# Lesson 191: Add the __func__ identifier

Original chibicc commit: [`ba6b4b63751ed65f2fcd74965d2b337a1a65752b`](https://github.com/rui314/chibicc/commit/ba6b4b63751ed65f2fcd74965d2b337a1a65752b).
Earlier explanations are available in Git history.

Every function definition now binds `__func__` in its function scope to a
static character array containing its name and a terminating zero. It is a
parser-provided variable, not a preprocessor macro. Its array size is therefore
the name length plus one, and returning its address is safe after the call.

The parser creates an ordinary anonymous global string object and a scoped
binding for it. This also creates an unused string for functions that never
reference __func__, matching the original C commit. Tests now select function
objects explicitly because each function also adds a string object. Instruction
snapshots omit global data; separate tests inspect the generated string and
assemble/link/run the complete emitted output. Anonymous label numbers change
because those strings consume identifiers.

```sh
printf 'int main(void){return sizeof(__func__);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 5 for main plus its terminating zero
```

Assembly emits the bytes of main and a zero in static data. The sizeof
expression produces a constant 5, which is loaded into `%rax` and returned.
Tests cover array size, character access, returning the string, local shadowing,
rejection outside functions, original fixtures and earlier AST/assembly checks.

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
