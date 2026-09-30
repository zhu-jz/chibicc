# Lesson 70: Return type conversions

Original chibicc commit: [`818352acc07d0a982076b4b49345b42be706f5e1`](https://github.com/rui314/chibicc/commit/818352acc07d0a982076b4b49345b42be706f5e1).
Earlier explanations are available in Git history.

## What changed

The parser keeps the current function object while reading its body. Each return
expression is annotated and wrapped in a cast to that function's return type.
This makes narrow integer returns truncate/sign-extend correctly and preserves
pointer result types. The same cast builder serves explicit, arithmetic,
assignment, and now return conversions. Bare `return;` remains unsupported.

Python stores current_fn on the parser instance rather than in a C global.
Existing grammar checks inspect through the new return wrapper; dedicated tests
check the wrapper itself. The original's conversion table still implements a
long-to-int conversion without an extra instruction at this stage.

## Assembly and WSL example

```sh
printf 'char f(int x){return x;}int main(){return f(261);}\n' > /tmp/lesson70.c
python3 python/main.py /tmp/lesson70.c > /tmp/lesson70.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson70 /tmp/lesson70.s
/tmp/lesson70
echo $?
```

Before f returns, `movsbl %al, %eax` keeps the low byte of 261 (5) and interprets
it as a signed char. Main returns 5; `echo $?` displays it. Tests cover narrow
signed returns, long widening, pointer returns, typed return CAST nodes, and the
updated original function tests.

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
