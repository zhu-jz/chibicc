# Lesson 288: Use hash sets for keyword lookup

Original chibicc commit: [`f6944133d211ec6fb71c41f118905e16a752135b`](https://github.com/rui314/chibicc/commit/f6944133d211ec6fb71c41f118905e16a752135b).
Earlier explanations are available in Git history.

The lexer keyword list and parser type-keyword list are now immutable frozensets.
Membership uses hashing instead of scanning a tuple for every token. Type-name
recognition still checks visible typedefs when the spelling is not a built-in
keyword, so scope-dependent parsing remains intact.

```sh
printf 'typedef int T;int main(void){int integer=20;T value=22;return integer+value;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Keyword lookup happens while compiling. Assembly stores 20 and 22 in local slots,
loads them and adds them for the return. Tests distinguish keyword spellings from
longer identifiers and confirm typedef-based declarations, plus original fixtures.
Python uses frozenset because these maps contain only membership information;
C uses lazily initialized HashMap entries with a dummy value. The port keeps its
existing classification of inline as a keyword; its parsing behavior is unchanged.

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
