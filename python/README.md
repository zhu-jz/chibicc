# Lesson 216: Accept historical compatibility flags

Original chibicc commit: [`b1fdddff1523d2ca7bab4050434499d3a5ac39a1`](https://github.com/rui314/chibicc/commit/b1fdddff1523d2ca7bab4050434499d3a5ac39a1).
Earlier explanations are available in Git history.

The driver now ignores -O*, -W*, -g*, -std=* and the original commit's explicit
set of freestanding, builtin, frame-pointer, stack-protector, aliasing, target
and warning flags. This lets ordinary build commands run, but these accepted
flags do not enable optimization or change the language or target behavior.
Unrecognized flags outside that set still receive an error.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -O2 -Wall -g -std=c11 -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The assembly remains identical to a compile without these flags: mov $42
and the regular main epilogue. Tests compare full emitted output, check an
unknown option and run the original C fixtures. Python uses startswith and
a tuple of exact spellings in place of the original strcmp/strncmp chain.
Options are forwarded to cc1 as before and ignored there as well.

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
