# Lesson 285: Exercise the string hash map

Original chibicc commit: [`0aad326f3550b3d4c499d4078fcc65cc2dbf7626`](https://github.com/rui314/chibicc/commit/0aad326f3550b3d4c499d4078fcc65cc2dbf7626).
Earlier explanations are available in Git history.

The original adds an open-addressing string hash table and a -hashmap-test command.
It hashes keys into buckets, probes collisions, marks deleted slots with tombstones
and rehashes crowded tables. Compiler lookup sites are not changed in this commit.
For the Python port, the built-in dict already provides the required string map;
hashmap.py exercises insertion, deletion, reinsertion, missing keys and replacement.

```sh
python3 python/main.py -hashmap-test  # prints OK
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The self-test checks thousands of keys and exits without requiring a source file.
The compiler's assembly still returns 42 in rax; this commit adds internal data
structure testing without changing generated programs. The command is tested
through the compiler entry point, and hashmap.py is included in packaged builds.
Python deliberately uses its standard hash table rather than reproducing C's
bucket allocation, FNV hash, tombstones or memory management. Its self-test also
checks the actual removed keys and final inserted values; the original repeatedly
checks a generic missing key and mistakenly reinserts in its final checking loop.

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
