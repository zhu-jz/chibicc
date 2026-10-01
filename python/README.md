# Lesson 258: Omit the middle operand of a conditional

Original chibicc commit: [`e28a612e9c2293182a83d5a7c6f48129455ce951`](https://github.com/rui314/chibicc/commit/e28a612e9c2293182a83d5a7c6f48129455ce951).
Earlier explanations are available in Git history.

GNU `a ?: b` now saves a in an unnamed local and rewrites the expression as
`(tmp=a, tmp ? tmp : b)`. Saving the value is essential: an increment or function
call in a must run once, even though its value is both the condition and result.
The ordinary conditional type conversion still applies to the result branches.

```sh
printf 'int main(void){int x=41;int y=++x?:0;return y+(x!=42);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly increments x, stores its value into the compiler's temporary, tests that
saved value and reloads it for the true branch. The return also checks x stayed
42. Tests cover true and false branches, nested expressions, single evaluation,
floating and pointer values, plus the original arithmetic fixtures.
Python builds the same assignment, comma and conditional Nodes explicitly;
C allocates linked node structures. No dedicated assembly instruction is needed
for the extension because existing expression generation handles the rewrite.

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
