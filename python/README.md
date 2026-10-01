# Lesson 277: Strip executable symbols with -s

Original chibicc commit: [`c32f0e21e71f43e64a7b98c9d96d4c513d42ba37`](https://github.com/rui314/chibicc/commit/c32f0e21e71f43e64a7b98c9d96d4c513d42ba37).
Earlier explanations are available in Git history.

The driver accepts -s and keeps it in a separate list of extra linker arguments.
It passes those arguments to ld before the input objects. Stripping removes the
ordinary symbol table from the linked executable without changing its behavior.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -s -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
python3 python/main.py -s -o /tmp/lesson /tmp/lesson.c
nm /tmp/lesson
```

Assembly still defines main and returns 42 in rax. The linker resolves that name
before removing the final symbol table. Tests build both stripped and ordinary
executables, check their exit status and use nm to check whether main remains.
Python passes the extra argument list explicitly where C stores a global array.

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
