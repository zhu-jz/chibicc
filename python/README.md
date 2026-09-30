# Lesson 52: Struct tags and their scope

Original chibicc commit: [`e1e831ea3ee46ed7d4c975822f418d60d3050e1b`](https://github.com/rui314/chibicc/commit/e1e831ea3ee46ed7d4c975822f418d60d3050e1b).
Earlier explanations are available in Git history.

## What changed

A struct definition may now have a tag: `struct Point {int x; int y;};`.
Later `struct Point p;` retrieves that type from the nearest visible tag
binding. A tag-only definition needs no variable declaration. A definition
inside braces shadows an outer tag until the block ends.

Each Scope now holds separate variable and tag collections. A variable and
a tag may share a spelling: `int Point; struct Point p;` is unambiguous because
`struct` selects the tag collection. Python uses a dictionary for tags and
lists for variable bindings, replacing C's linked lists in its Scope records.
The declaration's type is still copied to attach a variable name without
changing the shared tag's type metadata.

This commit registers a tag after its definition finishes. Unknown tags are
errors; forward declarations and a self-referential struct are not supported
at this point. Layout and field access keep their previous aligned behavior.

## Assembly and WSL example

```sh
printf 'struct Point{int x;int y;}; int main(){struct Point p;p.x=20;p.y=22;return p.x+p.y;}\n' > /tmp/lesson52.c
python3 python/main.py -o /tmp/lesson52.s /tmp/lesson52.c
cat /tmp/lesson52.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson52 /tmp/lesson52.s
/tmp/lesson52
echo $?
```

The tag itself emits no instructions or storage. p occupies 16 bytes, with
fields at offsets 0 and 8. Member-address instructions and integer stores,
loads, and addition produce 42 in `%rax`; the shell displays exit status 42.
Tests cover upstream's four tagged-struct cases, global usage, inner/outer tag
scope, separate variable names, unknown tags, and the current self-reference
limit, alongside the complete C fixture suite.

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
