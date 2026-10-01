# Lesson 284: Allow static initializers containing label addresses

Original chibicc commit: [`f0c98e0d590ffae286a8a4847c91212c734be8e3`](https://github.com/rui314/chibicc/commit/f0c98e0d590ffae286a8a4847c91212c734be8e3).
Earlier explanations are available in Git history.

Label addresses can now appear in static initializers. A forward label's assembly
name is unknown while parsing the initializer, so its relocation retains a reference
to the label-expression node. After the function's labels are resolved, code generation
reads the finished name when emitting .quad. This enables static jump tables.

```sh
printf 'int main(void){static void *p[]={&&a,&&b};goto *p[1];a:return 1;b:return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly emits two .quad label entries in data, loads the second pointer and jumps
through rax to the return of 42. The assembler/linker resolve each entry's address.
Tests check forward static tables, single pointers, emitted relocations and missing
labels, plus the original control fixture. Python holds the node itself rather than
C's pointer to its unique_label field; stable global names remain ordinary strings.

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
