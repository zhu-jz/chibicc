# Lesson 168: Add #undef

Original chibicc commit: [`9ad60e41d512158d942d1bf3808682ede6ef5118`](https://github.com/rui314/chibicc/commit/9ad60e41d512158d942d1bf3808682ede6ef5118).
Earlier explanations are available in Git history.

`#undef NAME` makes that identifier cease to be a macro. Undefining an unknown
name is harmless; a later definition can give it a new body. The name must be
an identifier and extra tokens use the existing warning behavior.

The C macro list records a deleted entry to hide older definitions. Python's
dictionary already keeps only the latest definition, so removing its entry has
the same effect. Definitions in skipped branches remain untouched.

```sh
printf '#define VALUE 7\n#undef VALUE\nint main(void){int VALUE=42;return VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

After removal, `VALUE` is a local variable. Assembly stores 42 in its stack
slot and loads it for the return value in `%rax`. Tests cover overriding then
undefining, defining again, unknown names, skipped directives and restoring
keyword spellings. The original fixture now undefines its keyword macros.

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
