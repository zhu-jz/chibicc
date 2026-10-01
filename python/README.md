# Lesson 270: Treat preprocessing inputs as C automatically

Original chibicc commit: [`4064871212049d82af3632941d15e6a0757ebc3c`](https://github.com/rui314/chibicc/commit/4064871212049d82af3632941d15e6a0757ebc3c).
Earlier explanations are available in Git history.

After parsing options, -E now forces the language selection to C. This allows
preprocessing stdin or a file with an arbitrary suffix without explicitly using
-xc. Because the implication happens after all options, it also overrides an
explicit -x assembler or -x none when -E is present.

```sh
printf '#define VALUE 42\nint main(void){return VALUE;}\n' > /tmp/lesson.data
python3 python/main.py -E -o /tmp/lesson.c /tmp/lesson.data
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The first compiler invocation emits preprocessed C with VALUE replaced by 42;
the second emits assembly that loads and returns that constant. Tests verify
stdin, unknown suffixes and both explicit language overrides, alongside existing
language-selection and original fixture tests. Python stores the forced C string
where C stores its FILE_C enum. Object-file precedence remains unchanged.

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
