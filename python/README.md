# Lesson 123: Static global variable visibility

Original chibicc commit: [`eb85527656f77b9532f3a78cefde7a2eb739189e`](https://github.com/rui314/chibicc/commit/eb85527656f77b9532f3a78cefde7a2eb739189e).
Earlier explanations are available in Git history.

## What changed

File-scope static variables now emit `.local name`, giving their symbols internal
visibility. Ordinary global definitions retain `.globl name`. Anonymous globals,
including string literals, compound literals and static-local storage, default
to static too. Source-name lookup and byte initialization are unchanged.

Python stores the same is_static flag and chooses the assembler directive.
Function parsing already explicitly set its visibility, so the new anonymous
global default does not change ordinary function visibility. Tests use nm's
lowercase d to confirm a local initialized data symbol.

## Assembly and WSL example

```sh
printf 'static int g=42;int main(){return g;}\n' > /tmp/lesson123.c
printf 'int g=1;\n' > /tmp/lesson123-helper.c
python3 python/main.py /tmp/lesson123.c > /tmp/lesson123.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson123 /tmp/lesson123.s /tmp/lesson123-helper.c
/tmp/lesson123
echo $?
```

Our assembly's `.local g` permits the helper's separate global g without a symbol
collision. Main reads its own private value and returns 42. Tests check that link,
emitted visibility, parsed flags for public/private/anonymous objects, assembled
symbol visibility, actual execution, and updated original variable examples.

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
