# Lesson 287: Use hash maps for block-scope names

Original chibicc commit: [`655954e301621737988a4fa0a2c72ffc24285c8d`](https://github.com/rui314/chibicc/commit/655954e301621737988a4fa0a2c72ffc24285c8d).
Earlier explanations are available in Git history.

Each block now stores its ordinary names in a dictionary, alongside the existing
tag dictionary. Lookup searches blocks from innermost to outermost and performs
one map lookup per block. Adding a name replaces that block's binding; leaving a
block exposes the outer binding again. Global function lookup also uses the map.

```sh
printf 'int main(void){int answer=42;{int answer=1;}return answer;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly gives the two declarations separate stack slots and loads the outer
answer for the final return. The map affects parsing, not runtime storage.
Tests cover five hundred local names, nested shadowing, separate ordinary/tag
namespaces, typedef shadowing and existing inline-function liveness.
Python removes the redundant VarScope name field and uses standard dictionaries
where C uses HashMap. Tag maps were already dictionaries in this port. Object
references remain shared so completing a struct updates earlier declarations.

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
