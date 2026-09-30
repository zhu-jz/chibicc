# Lesson 64: Typedef names and scope

Original chibicc commit: [`a6b82da1ae9eefa44dada0baa885c283823ad59a`](https://github.com/rui314/chibicc/commit/a6b82da1ae9eefa44dada0baa885c283823ad59a).
Earlier explanations are available in Git history.

## What changed

Typedef creates a name for a type: `typedef int T;`, `typedef int Row[3];`, or
`typedef struct {int a;} S;`. An alias is available wherever a type is parsed,
including parameters and members. It creates no variable, stack slot, data
symbol, or executable instruction. Comma-separated aliases and an empty
`typedef int;` are accepted as in upstream; `typedef t;` defaults to int.

Variable scope entries now distinguish an object binding from a type_def
binding. Lookup stops at the nearest name either way, so a variable can hide
a typedef. `typedef int t; t t=3;` first uses the alias as the type, then
registers the second t as a variable. The declaration-specifier parser stops
after the already-selected type rather than consuming that name a second time.
Block scope restores an outer alias after the inner binding ends. Struct/union
tags still have their separate name space.

VarAttr carries the typedef flag while declaration specifiers are parsed.
Parameters and struct members pass no attributes and reject typedef there.
Python dataclasses and lists represent C's scope records; copying a named
declaration's Type keeps shared aliases' name metadata intact. Function-call
signature, return-conversion, and aggregate ABI limits remain at this stage.

## Assembly and WSL example

```sh
printf 'typedef int T;int main(){T x=42;return x;}\n' > /tmp/lesson64.c
python3 python/main.py -o /tmp/lesson64.s /tmp/lesson64.c
cat /tmp/lesson64.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson64 /tmp/lesson64.s
/tmp/lesson64
echo $?
```

Only x occupies storage: it is a four-byte int at -4(%rbp). The existing
`%eax` store and sign-extending int load return 42; the shell displays its
status. Tests cover all upstream alias cases, arrays and pointer-to-array
aliases, aliased return/parameter types, shadowing, no typedef storage, and
invalid alias expressions/contexts. The new upstream typedef fixture runs
with every other C fixture; the full Python suite is also checked.

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
