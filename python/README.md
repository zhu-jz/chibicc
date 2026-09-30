# Lesson 60: Function declarations

Original chibicc commit: [`74e3acc296d90d6d16ae70803196e967564fb16a`](https://github.com/rui314/chibicc/commit/74e3acc296d90d6d16ae70803196e967564fb16a).
Earlier explanations are available in Git history.

## What changed

A top-level function declarator may now end with `;`, producing a declaration
without a body: `int f(int x);`. Obj records is_function and is_definition
separately. Declarations keep their function type and name in global scope
but allocate no parameter/local objects. A following `{...}` marks a definition,
and codegen emits a function only for definitions.

A declaration can precede a definition, or describe a function provided by a
linked helper or library. Upstream's test header now declares `int printf();`.
The compiler may retain separate objects for a declaration and a definition,
but only one body contributes instructions. Python uses the same Obj dataclass
with an added boolean, following upstream's unified object model.

This stage still requires parameter names when parameters are written, so
`int f(int x);` is accepted but `int f(int);` is not. Calls still default to
long type and do not yet enforce signatures; declarations do not implement
full prototype compatibility, indirect calls or aggregate calling rules.

## Assembly and WSL example

```sh
printf 'int f(int x);int main(){return f(42);}int f(int x){return x;}\n' > /tmp/lesson60.c
python3 python/main.py -o /tmp/lesson60.s /tmp/lesson60.c
cat /tmp/lesson60.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson60 /tmp/lesson60.s
/tmp/lesson60
echo $?
```

The declaration emits no label or storage. main supplies 42 in `%rdi` and
calls f; f saves `%edi` into its four-byte parameter slot, reloads it with
sign extension, and returns. The shell reports status 42. Tests check a
forward declaration/definition, an external GCC-built helper, the definition
flag and empty declaration storage, exactly one emitted body, the named
parameter limit, and the C fixture suite with its updated header.

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
