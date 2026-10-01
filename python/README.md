# Lesson 170: Stop recursive object-like expansion with hidesets

Original chibicc commit: [`acce00228b842af35df5af8c97398765a386ab1e`](https://github.com/rui314/chibicc/commit/acce00228b842af35df5af8c97398765a386ab1e).
Earlier explanations are available in Git history.

Each token now carries a set of macro names already used in its expansion.
Expanding a macro copies its replacement tokens, combines their existing
hidesets with the invoking token's hideset, and adds the current macro name.
A name found in its own token's hideset is passed through without expansion.
This stops both direct and indirect recursion while permitting other expansions.

Python uses immutable `frozenset` values instead of C linked lists. Shared sets
cannot accidentally change a different token's expansion history, and set union
expresses the original operation directly.

```sh
printf 'int main(void){int VALUE=6;\n#define VALUE VALUE+3\nreturn VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 9
```

The return expression becomes `VALUE+3`, where the surviving identifier refers
to the local variable. Assembly loads that variable, adds 3 and returns 9 in
`%rax`. Tests inspect hidesets, run direct and indirect recursion, and check
preprocessing finishes within a timeout. The complete source and packaged
compiler suites are also checked at this milestone.

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
