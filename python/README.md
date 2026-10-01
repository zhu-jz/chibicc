# Lesson 99: Discard excess initializer elements

Original chibicc commit: [`a754732c046939cd87ac9fc8e9483ae9b3369449`](https://github.com/rui314/chibicc/commit/a754732c046939cd87ac9fc8e9483ae9b3369449).
Earlier explanations are available in Git history.

## What changed

An array initializer now reads to its closing brace rather than stopping after
the declared element count. Elements that fit populate the initializer tree;
excess elements are parsed but discarded. Their runtime side effects and calls
are never emitted. Omitted elements still become zero. This original commit
silently discards excess values, unlike GCC's usual diagnostic for excess items.

Python's skip_excess_element returns the next token index; C returns a Token
pointer. The historical helper accepts an expression optionally wrapped in nested
single-element braces; it does not yet skip an arbitrary comma-separated list
inside an excess braced aggregate. Trailing commas remain unsupported.

## Assembly and WSL example

```sh
printf 'int main(){int i=0;int a[1]={42,++i};return a[0]+i;}\n' > /tmp/lesson99.c
python3 python/main.py /tmp/lesson99.c > /tmp/lesson99.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson99 /tmp/lesson99.s
/tmp/lesson99
echo $?
```

The emitter clears/stores a[0]; it emits no increment for the discarded ++i.
Main returns 42. Parsing can still allocate compiler temporaries or report
undefined names in discarded input. Tests cover excess scalar/nested values,
skipped increments and unresolved external calls, malformed excess input,
assembly omission, real executables, and all original fixture programs.

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
