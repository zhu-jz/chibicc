# Lesson 304: Forward comma-separated linker options with -Wl,

Original chibicc commit: [`d1bc9a4eb0e205b10a583c347a9fe7d4bed7b813`](https://github.com/rui314/chibicc/commit/d1bc9a4eb0e205b10a583c347a9fe7d4bed7b813).
Earlier explanations are available in Git history.

Arguments starting with -Wl, are now kept as linker inputs rather than discarded
with compatibility warning flags. The driver splits their comma-separated parts
and passes those parts to ld at that position in the input order. Empty parts are
skipped, matching C's strtok behavior.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -Wl,--gc-sections -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
python3 python/main.py -Wl,--gc-sections -o /tmp/lesson /tmp/lesson.c
```

The option changes the linker command, while main's assembly still returns 42.
Tests build duplicate function definitions, verify that ordinary linking fails,
then forward -z,muldefs,--gc-sections and run the resulting executable. They also
check empty comma fields and traced ordering. Python splits strings into argument
lists instead of duplicating and mutating a C buffer; no shell interprets the parts.
The original driver fixture invokes native cc for its -Wl check, so our direct
Python-driver test verifies the new path explicitly.

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
