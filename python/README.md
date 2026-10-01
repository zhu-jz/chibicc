# Lesson 286: Look up macro names through a hash map

Original chibicc commit: [`30520e5a7c73a6613cfcef38d72058e7cccde1f4`](https://github.com/rui314/chibicc/commit/30520e5a7c73a6613cfcef38d72058e7cccde1f4).
Earlier explanations are available in Git history.

The original preprocessor replaces its linked macro list with a hash map. Defining
a name replaces its map entry; undefining it deletes the entry. A token's exact
name is the lookup key, so similarly prefixed names remain distinct. This improves
lookup cost while preserving macro expansion and redefinition behavior.

```sh
printf '#define ANSWER 1\n#undef ANSWER\n#define ANSWER 42\nint main(void){return ANSWER;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The preprocessor expands the latest definition before parsing. Assembly moves 42
to the return register; macro lookup happens entirely during compilation.
Python already used dict for macros in earlier lessons, so this commit documents
that correspondence and tests one thousand definitions, exact prefix distinctions,
delete/redefine and deleting a missing name. Existing macro tests remain enabled.
Python copies token spelling into a string key instead of C's pointer-plus-length
hash lookup, and its dictionary manages storage automatically.

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
