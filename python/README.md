# Lesson 219: Return zero when main reaches its end

Original chibicc commit: [`9c36dd727c736dc3a3ffa6ce7ce473966d802068`](https://github.com/rui314/chibicc/commit/9c36dd727c736dc3a3ffa6ce7ce473966d802068).
Earlier explanations are available in Git history.

Reaching the closing brace of main now returns zero, as required by C. The
compiler emits mov $0, %rax just before main's return label. An explicit
return jumps directly to that label, bypassing the new instruction and
preserving its value. Other functions receive no implicit return value.

```sh
printf 'int main(void){42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 0
```

The expression first loads 42, then the fallthrough instruction replaces it
with zero. Adding return before 42 makes the explicit path exit with 42.
Tests run empty, expression-ending and call-ending mains, preserve explicit
returns, verify the label placement and run the original fixture whose final
return is removed. Existing main assembly snapshots include the new default.
Python uses a direct name comparison; the generated behavior matches C.

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
