# Lesson 213: Align zero-width bitfields

Original chibicc commit: [`17ea802ceaa76f55726488379959a983f891f631`](https://github.com/rui314/chibicc/commit/17ea802ceaa76f55726488379959a983f891f631).
Earlier explanations are available in Git history.

An unnamed zero-width bitfield now moves the bit cursor to the next boundary
of its declared storage type. It allocates no value bits, but affects where
following members begin. Struct size still rounds up to the aggregate alignment.
Python's integer cursor and align_to perform the same layout operation as C.

```sh
printf 'int main(void){return sizeof(struct T{int a:3;int:0;int b:5;})+34;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The first field uses one int storage unit and the barrier starts b in another;
sizeof is 8, emitted as an immediate. Adding 34 leaves 42 in rax. Tests check
leading and trailing barriers, a long alignment boundary, member offsets and
original fixtures. This commit adds layout only; anonymous initializer and
address-taking rules remain at their current historical behavior.

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
