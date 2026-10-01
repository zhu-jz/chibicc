# Lesson 208: Define macros from command-line options

Original chibicc commit: [`fc69f5c6f9b3aeb5d6ee61353f0ed0df28f954c5`](https://github.com/rui314/chibicc/commit/fc69f5c6f9b3aeb5d6ee61353f0ed0df28f954c5).
Earlier explanations are available in Git history.

-DNAME defines NAME as 1; -DNAME=value uses the replacement text after the
first equals sign. Both attached and separate forms work, and -DNAME= is
empty. Definitions are applied in command-line order after predefined macros.
Internal compiler subprocesses receive the same options for every input file.

Python passes an explicit macro dictionary through parsing and preprocessing
rather than introducing C global state. Direct preprocess calls still get a
fresh default dictionary. A missing separate -D value gets a usage error
instead of the original's unchecked access past the argument array.

```sh
printf 'int main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -DANSWER=42 -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

ANSWER becomes a numeric token before parsing, so the assembly contains the
ordinary mov $42 and return path. Tests check both option forms, empty values,
redefinition order, predefined overrides, #if, the executable driver and
upstream C fixtures. This step adds object-like command-line macros only.

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
