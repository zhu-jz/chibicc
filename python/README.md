# Lesson 299: Honor pragma once

Original chibicc commit: [`a6c662207d38813b3dd490d81d8afe14ac99272b`](https://github.com/rui314/chibicc/commit/a6c662207d38813b3dd490d81d8afe14ac99272b).
Earlier explanations are available in Git history.

#pragma once now marks the current physical file as already included. A later
include of the same path skips it before guard detection or opening the file.
The marker takes effect while preprocessing, so a file can safely include itself
after its pragma. Other pragmas retain the existing ignored behavior.

```sh
printf '#pragma once\nint answer=42;\n' > /tmp/lesson-answer.h
printf '#include "lesson-answer.h"\n#include "lesson-answer.h"\nint main(void){return answer;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly defines answer once, reads it and returns 42. Tests count reads of a
self-including header, repeat separate compilations, update the old ignored-once
expectation and run the original pragma-once.c fixture. Python stores the once
flag on its File records, scoped to the current file list, rather than a C global
path map. Both compare physical path spellings; neither canonicalizes aliases.
The existing extra-token handling of skip_line is preserved.

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
