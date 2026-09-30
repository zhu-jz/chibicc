# Lesson 69: Declared function calls

Original chibicc commit: [`9e211cbf1d459babf035fd6b3407c2bd184cb639`](https://github.com/rui314/chibicc/commit/9e211cbf1d459babf035fd6b3407c2bd184cb639).
Earlier explanations are available in Git history.

## What changed

A call now looks up its identifier in the current scopes. Missing declarations
produce `implicit declaration of a function`; a variable or typedef used as a
callee produces `not a function`. Definitions declare their own names before
parsing their bodies, so recursion works. Forward and externally linked calls
need prototypes. Call nodes retain the declared return type, and arguments are
annotated before attaching them to a typed call node.

The original diagnostic formatter no longer exits internally. Python already
raises CompileError and formats it at the command-line boundary, so no matching
change is needed. Parameter conversions remain incomplete at this stage.

## Assembly and WSL example

```sh
printf 'int f();int main(){return f();}int f(){return 42;}\n' > /tmp/lesson69.c
python3 python/main.py /tmp/lesson69.c > /tmp/lesson69.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson69 /tmp/lesson69.s
/tmp/lesson69
echo $?
```

`call f` pushes a return address and transfers control to f. Its return value
comes back in eax/rax and main returns it; the shell displays 42. Declaring f
emits no function body. Tests check prototypes, recursion, return-type metadata,
undeclared/shadowed callees, assembly, and all upstream programs.

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
