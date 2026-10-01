# Lesson 261: Emit only reachable static inline functions

Original chibicc commit: [`e5f4ca90fd2bf950189c98ed7f1873c9f35131f3`](https://github.com/rui314/chibicc/commit/e5f4ca90fd2bf950189c98ed7f1873c9f35131f3).
Earlier explanations are available in Git history.

Functions now record referenced function names. Ordinary functions are roots;
static inline functions become live only through references from live functions.
A recursive walk marks each function before following its references, which
handles recursive cycles without repeatedly traversing them. Code generation
skips function bodies that remain unmarked.

```sh
printf 'static inline int unused(void){return 0;}static inline int f(void){return 42;}int main(void){return f();}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly contains main and f but no unused label or body. Main still calls f;
this is removal of unused bodies, not call-site inlining. Tests check direct and
transitive references, unused and referenced cycles, ordinary static roots and
extern inline roots, and run original fixtures and translated driver scenarios.
Python stores reference names in a list instead of C's growable StringArray.
The original current-function state persists after a definition, so later
file-scope references can be attached to that last function. This historical
state behavior is retained. Literal data created while parsing dead bodies may
also remain in the assembly; the original step only skips function text.

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
