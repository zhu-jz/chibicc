# Lesson 295: Exclude include-path headers from dependencies with -MMD

Original chibicc commit: [`c3edffbbb06be9d586ee4f1cf678049b7d81369d`](https://github.com/rui314/chibicc/commit/c3edffbbb06be9d586ee4f1cf678049b7d81369d).
Earlier explanations are available in Git history.

-MMD enables dependency generation during compilation, like -MD, and filters files
whose paths begin with a recorded include-directory prefix followed by '/'. The
same filter applies to -MP dummy rules. The driver records its include-path list
after adding the default directories.

```sh
printf '#define ANSWER 42\n' > /tmp/lesson-answer.h
printf '#include "lesson-answer.h"\n#include <stddef.h>\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -S -MMD -MF /tmp/lesson.d -o /tmp/lesson.s /tmp/lesson.c
cat /tmp/lesson.d
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The rule lists the source and its local quoted header, but omits the bundled
stddef.h. Assembly still returns 42. Tests compare -MD and -MMD and check both
prerequisites and dummy rules. This original copies the entire include list,
including user -I directories, so their headers are also omitted; that historical
behavior remains. Python returns a tuple of recorded paths instead of filling a
C global array, and uses string-prefix checks without resolving filesystem paths.

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
