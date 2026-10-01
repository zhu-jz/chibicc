# Lesson 186: Add default include paths

Original chibicc commit: [`a939a7a90638631c296dfb63d857b24555b25327`](https://github.com/rui314/chibicc/commit/a939a7a90638631c296dfb63d857b24555b25327).
Earlier explanations are available in Git history.

The internal compiler now appends default search directories after user `-I`
entries: `include/` beside its entry point, `/usr/local/include`,
`/usr/include/x86_64-linux-gnu`, and `/usr/include`. The order follows the C
commit. Quoted includes still try their source directory first.

For Python, the entry point is main.py or the packaged .pyz file, so each can
find an adjacent include directory. Defaults are added only in the internal
compilation process, avoiding duplicates in the driver. No new bundled headers
are introduced in this original commit. Finding system headers does not imply
that every header's language/preprocessor features are supported yet.

```sh
printf '#include <linux/limits.h>\nint main(void){return PATH_MAX/128;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 32 on Ubuntu, where PATH_MAX is 4096
```

The header's constant expands into integer division. Assembly computes its
quotient, leaves 32 in `%rax`, and returns. Tests verify search ordering, an
adjacent header for a freshly packaged compiler, and Ubuntu's Linux limits
header when installed. Original C sources remain unchanged.

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
