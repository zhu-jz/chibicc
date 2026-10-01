# Lesson 176: Stop recursive function-like expansion

Original chibicc commit: [`1313fc6d3a77cedbca18fa0ffee1a86d0903ad7f`](https://github.com/rui314/chibicc/commit/1313fc6d3a77cedbca18fa0ffee1a86d0903ad7f).
Earlier explanations are available in Git history.

Function-like expansion now attaches a hideset to every substituted token.
It intersects the invoking name's hideset with the closing parenthesis's set,
then adds the macro name. Arguments keep their own existing hidesets as well.
An intersection handles invocations whose name and punctuation came from
different expansion histories; using a union would suppress too much.

Python's immutable set intersection and union replace linked-list operations.
Direct and indirect function-like recursion now stop. A surviving name can
still refer to a real C function with the same name, just as a recursive
object-like macro can leave a variable reference.

```sh
printf 'int value(int x){return x;}\n#define value(x) value(x)+1\nint main(void){return value(41);}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Expansion leaves a real call to `value(41)` followed by `+1`. Assembly passes
41 in `%rdi`, calls the function through `%rax`, adds one to its result, and
returns 42. Tests exercise direct and indirect recursion, nested invocation,
the intersection case, and preprocessing termination within a timeout.

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
