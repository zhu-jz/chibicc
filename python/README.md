# Lesson 222: Expand the GNU counter macro

Original chibicc commit: [`0e77f3dff8b44547da4639c9609c216c9c896fa5`](https://github.com/rui314/chibicc/commit/0e77f3dff8b44547da4639c9609c216c9c896fa5).
Earlier explanations are available in Git history.

__COUNTER__ now expands to 0, 1, 2 and so on as preprocessing requests its
replacement. It is a dynamic macro handler, so nested macro expansion and
conditional expressions participate in the same sequence. Skipped branches
consume no counter values. Expanded numbers then enter the normal PP_NUM
conversion pass.

```sh
printf 'int main(void){return __COUNTER__+__COUNTER__+41;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Preprocessing replaces the two uses with 0 and 1; normal addition returns
42. Tests cover the sequence, expansion through another macro, #if consumption,
skipped branches, two-stage token pasting and original fixtures. Python keeps
the counter in a closure belonging to its macro dictionary rather than C's
static process variable. A fresh independent preprocess call restarts at zero;
within one compilation, includes and macro expansion share the sequence.

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
