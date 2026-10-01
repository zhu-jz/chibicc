# Lesson 263: Accept the historical idirafter driver option

Original chibicc commit: [`11fc259b01c4a855e53ffdb2b86c1030f9c18586`](https://github.com/rui314/chibicc/commit/11fc259b01c4a855e53ffdb2b86c1030f9c18586).
Earlier explanations are available in Git history.

The driver recognizes `-idirafter DIR`, consumes its argument and appends entries
after explicitly requested -I directories. This original patch mistakenly stores
the literal option text `-idirafter`, not DIR. We retain the actual historical
behavior, including searching a directory literally named -idirafter if present.
Default system include paths are appended later by the internal compiler stage.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -idirafter /tmp -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

This input needs no include, so assembly loads and returns 42 normally. Tests
reproduce the original driver priority checks, then additionally show that DIR
alone is not searched and the literal option directory is. A missing argument
reports usage rather than indexing past the argument list.
Python separates a deferred list from its ordinary include-path list as C does
with StringArray. This step records the original implementation's bug honestly;
it does not claim working standard idirafter semantics that the commit lacks.

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
