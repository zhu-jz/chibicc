# Lesson 298: Skip headers whose include guard is already defined

Original chibicc commit: [`d48d9e5ae35b5eb1a9dcb0c07c1dba9e65bd83f3`](https://github.com/rui314/chibicc/commit/d48d9e5ae35b5eb1a9dcb0c07c1dba9e65bd83f3).
Earlier explanations are available in Git history.

The preprocessor detects a common guard pattern: a file starts with #ifndef NAME
and #define NAME, and ends with #endif. It remembers the guard name for that path.
On later includes, a currently defined guard lets it skip opening and tokenizing
the file. Undefining the guard makes a later include read the header again.

```sh
printf '#ifndef LESSON_H\n#define LESSON_H\nint answer=42;\n#endif\n' > /tmp/lesson-answer.h
printf '#include "lesson-answer.h"\n#include "lesson-answer.h"\nint main(void){return answer;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly defines answer once and returns its value. Tests count header reads,
check input-file recording, and confirm rereading after #undef. Original C programs
remain in the regression suite. Python stores path-to-guard names in a dictionary.
The detector preserves this commit's syntactic scan, including its ineffective
nested-group check; it does not analyze every conditional shape or canonicalize
paths. Headers with content after their final #endif are not recognized.

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
