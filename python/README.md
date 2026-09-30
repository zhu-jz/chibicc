# Lesson 31: Unified variable and function objects

Original chibicc commit: [`0b7663481d0513067e0c0af04765b8578ae2a498`](https://github.com/rui314/chibicc/commit/0b7663481d0513067e0c0af04765b8578ae2a498).
Earlier explanations are available in Git history.

## What changed

Upstream merges its Function and variable structures into Obj, without a
language change. The Python port follows: Obj holds a name/type, local and
function flags, a local offset, and optional function body/parameters/locals.
The separate Function dataclass is removed.

Local construction marks `is_local`; function construction creates a global
object and marks `is_function`. Top-level objects are prepended, so their
emission order is reversed, matching upstream's linked-list behavior. Local
objects still belong to individual function frames. Code generation skips
non-function objects and explicitly selects `.text` before each function.

## Run it

```sh
python3 python/main.py 'int helper(){return 3;} int main(){return helper();}' > /tmp/lesson31.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson31 /tmp/lesson31.s
/tmp/lesson31
echo $?
```

The executable prints nothing; the last command shows **3**. Use an interactive
shell without `set -e` for nonzero statuses. Assembly emits main first here,
then helper; calls are resolved regardless of emission order. Function-specific
return labels and frame cleanup are unchanged.

Tests verify unified objects, flags, object order, `.text`, calls, parameters,
and exact assembly. No global-variable syntax is added in this commit.
Python lists replace the original object linked lists; no new behavioral
Python/C differences are introduced.

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
