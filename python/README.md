# Lesson 185: Add include directory options

Original chibicc commit: [`a1dd6213c85dfa6f36f74fd00ade09ed9fa3e467`](https://github.com/rui314/chibicc/commit/a1dd6213c85dfa6f36f74fd00ade09ed9fa3e467).
Earlier explanations are available in Git history.

`-I<dir>` appends a directory to the include search list. Directories are tried
in command-line order. A quoted filename first tries beside its source file;
an angle-bracket filename goes directly to the search list. If no candidate
exists, the literal filename is still tried as in the previous lesson.

The driver forwards its options when re-executing the compiler, and explicit
Python function arguments carry the search list through preprocessing. The
upstream fixture runner now supplies its test directory, matching the C
Makefile. This historical CLI supports the attached form only: use `-I/tmp`,
not a separate `-I /tmp` pair. A trailing bare `-I` is rejected by the precheck.

```sh
mkdir -p /tmp/lesson-include
printf '#define VALUE 42\n' > /tmp/lesson-include/answer.h
printf '#include <answer.h>\nint main(void){return VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -I/tmp/lesson-include -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The selected header defines VALUE; the function assembly loads 42 into `%rax`
and returns. Tests check quote versus angle precedence, directory ordering,
option forwarding, failed lookup and a missing option operand.

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
