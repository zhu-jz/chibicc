# Lesson 303: Search library directories with -L

Original chibicc commit: [`c8df7874c607f14eac3774680b55ab22c3aaf370`](https://github.com/rui314/chibicc/commit/c8df7874c607f14eac3774680b55ab22c3aaf370).
Earlier explanations are available in Git history.

The driver accepts both -LDIR and -L DIR and passes them to ld as a directory-search
argument. Existing -lname inputs can then resolve libraries outside the built-in
search directories. These options affect linking; header searches still use -I.

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson-library.c
python3 python/main.py -c -o /tmp/lesson-library.o /tmp/lesson-library.c
ar rcs /tmp/liblessonanswer.a /tmp/lesson-library.o
printf 'int answer(void);int main(void){return answer();}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -L/tmp -o /tmp/lesson /tmp/lesson.s -llessonanswer
/tmp/lesson
echo $?  # 42
python3 python/main.py -L /tmp -o /tmp/lesson /tmp/lesson.c -llessonanswer
```

The caller's assembly calls answer; ld searches /tmp for liblessonanswer.a and
extracts its definition. Tests build a real archive from Python-compiled code,
link and run it through the Python driver with both option forms. Python keeps
-L and its directory as separate subprocess arguments. It reports a missing
separate -L argument instead of C's unchecked argv access in this commit.

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
