# Lesson 240: Infer array bounds from designated elements

Original chibicc commit: [`835cd24b2c4598ee784d8bfd1c0427bfa948b947`](https://github.com/rui314/chibicc/commit/835cd24b2c4598ee784d8bfd1c0427bfa948b947).
Earlier explanations are available in Git history.

The array-bound counting pass now tracks the initializer cursor and its
maximum position. A designator can move backward without shrinking the bound,
or forward beyond the number of explicit values. Nested initializer parsing
handles the continuation needed to count rows. The completed array is then
initialized by the existing designator pass.

```sh
printf 'int main(void){int x[]={[0]=12,[3]=30};return x[0]+x[3]+x[1]+x[2];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The inferred bound is four; zeroing fills the two gaps and indexed stores
supply 12 and 30. Tests check forward and backward designators, computed
indices, inferred rows, global size and original fixtures. Python uses a
dummy initializer plus local index/maximum variables where C uses output
pointers. The original redundantly repeats its flexible-array check; Python
keeps one equivalent check. Range syntax is recognized only by this counting
pass at this step; range assignment has not yet been added.

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
