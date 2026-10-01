# Lesson 268: Prepend headers with the include driver option

Original chibicc commit: [`8f5ff07dc08d258209adf60ed8e796efa7b7a476`](https://github.com/rui314/chibicc/commit/8f5ff07dc08d258209adf60ed8e796efa7b7a476).
Earlier explanations are available in Git history.

`-include HEADER` now tokenizes a header before the main input. Repeated options
prepend their headers in command-line order, and all tokens share one preprocessing
pass. A directly existing path wins; otherwise include paths are searched.
Each physical file keeps its own source metadata, while __BASE_FILE__ stays the
main input filename.

```sh
printf '#define VALUE 42\n' > /tmp/lesson.h
printf 'int main(void){return VALUE;}\n' > /tmp/lesson.c
python3 python/main.py -include /tmp/lesson.h -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The forced header defines VALUE before main is read, so assembly loads 42 and
returns. Tests exercise ordered macros across two forced headers, include-path
lookup, missing headers, root-file identity, stdio.h and a real linked executable,
plus original fixtures. Python concatenates token lists without their intermediate
EOF tokens instead of relinking C chains. It uses immutable empty defaults for
optional header lists, avoiding shared mutable defaults between compilations.

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
