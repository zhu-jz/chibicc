# Lesson 241: Allow GNU designators without an equals sign

Original chibicc commit: [`691c4fac1529eaf1d825ca6093800912a4df3c91`](https://github.com/rui314/chibicc/commit/691c4fac1529eaf1d825ca6093800912a4df3c91).
Earlier explanations are available in Git history.

The GNU initializer extension now allows [index] value as well as [index]=value.
Designation consumes = when present, then uses the existing initializer parser.
Nested designators and omitted array bounds follow the same cursor rules.
This changes syntax acceptance; it adds no new initializer tree or codegen path.

```sh
printf 'int main(void){return ((int[10]){[3]42})[3];}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The compound literal is zeroed, its element three is assigned 42, and the
indexed load returns that value. Tests cover compound literals, globals with
inferred bounds, nested arrays, continuation values and original fixtures.
Python advances its token index conditionally where C advances a token pointer.
The optional equals sign follows the original GNU extension rather than strict
standard C designated-initializer syntax.

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
