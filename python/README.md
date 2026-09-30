# Lesson 62: Combined type specifiers

Original chibicc commit: [`287906abb85081b961e118bb80b30decb93fba6f`](https://github.com/rui314/chibicc/commit/287906abb85081b961e118bb80b30decb93fba6f).
Earlier explanations are available in Git history.

## What changed

The declaration-specifier parser consumes a sequence of type words. Short and
long may include int, in either order: `short int`, `int short`, `long int`,
and `int long` select the same types as short and long. Char, void and plain
int remain single-word types. Invalid built-in combinations such as `char int`
and duplicate `int` are diagnosed at the word that makes the combination bad.

C packs keyword counts into one integer and switches on the result. Python
keeps the seen words in a list and looks up their sorted tuple in a small table
of permitted combinations. This readable representation replaces the bitfield
trick without changing the accepted built-in combinations.

The upstream commit message mentions `long long`, but its actual switch has
no case for two longs. This port follows the code: `long long` is rejected.
The parser also defaults to int when no type word occurs in a context that
calls declspec, so `main(){...}` and an implicitly typed named parameter work.
This is an intermediate older-C behavior, not full modern declaration checking.
Struct/union combination validation and other storage/type words are incomplete.

## Assembly and WSL example

```sh
printf 'int main(){int long x=42;return x;}\n' > /tmp/lesson62.c
python3 python/main.py -o /tmp/lesson62.s /tmp/lesson62.c
cat /tmp/lesson62.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson62 /tmp/lesson62.s
/tmp/lesson62
echo $?
```

`int long` selects the eight-byte long type: the variable uses a full `%rax`
store/load at -8(%rbp), then returns 42. No new machine instruction implements
the alternate spelling. Tests cover every upstream combination, the implicit
int cases, invalid words/duplicates, and the actual long-long restriction.
The new upstream declaration fixture runs with the complete C fixture suite.

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
