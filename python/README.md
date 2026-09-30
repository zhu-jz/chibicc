# Lesson 75: File-scope static functions

Original chibicc commit: [`736232f3d672dae9a1ddae800909204c17fbe37c`](https://github.com/rui314/chibicc/commit/736232f3d672dae9a1ddae800909204c17fbe37c).
Earlier explanations are available in Git history.

## What changed

A static function gets internal linkage: its assembly symbol is local to the
object file. Other source files may define a different static function with the
same name without a link conflict. The parser records the static attribute on
function declarations and definitions; typedef combined with static is an error.
Storage classes remain invalid in parameter/type-name/member contexts.

At this historical step static affects functions only. Static variable storage
and complete redeclaration/linkage rules are not implemented yet. Python bool
fields replace the original C attributes without changing emitted behavior.

## Assembly and WSL example

```sh
printf 'static int f(){return 42;}int main(){return f();}\n' > /tmp/lesson75.c
python3 python/main.py /tmp/lesson75.c > /tmp/lesson75.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson75 /tmp/lesson75.s
/tmp/lesson75
echo $?
nm /tmp/lesson75 | grep ' f$'
```

`.local f` makes f a local symbol (nm prints lowercase t), while `.globl main`
keeps main externally visible. `call f` still invokes it normally. The program
returns 42. Tests link another C file containing its own static f, check assembly
visibility and declaration attributes, exercise errors, and run upstream tests.

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
