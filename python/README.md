# Lesson 116: Extern global declarations

Original chibicc commit: [`006a45ccd475296ee19ec87891523d89ce3f2f24`](https://github.com/rui314/chibicc/commit/006a45ccd475296ee19ec87891523d89ce3f2f24).
Earlier explanations are available in Git history.

## What changed

`extern int g;` now declares a global without defining storage. References still
use its symbol; the linker supplies its definition from another object. Objects
track is_definition, ordinary globals and string objects set it, and data emission
skips declarations. Function prototypes remain nondefinitions too.

Python booleans and fields mirror upstream storage attributes. This step handles
file-scope extern variables; block-scope behavior is unchanged. An extern with
an initializer also remains a nondefinition in this historical parser. Upstream's
new storage-class check rejects typedef only when both static and extern are
also present, so it temporarily accepts some invalid two-class combinations.
Tests preserve that exact change instead of implementing later validation.

## Assembly and WSL example

```sh
printf 'extern int g;int main(){return g;}\n' > /tmp/lesson116.c
printf 'int g=42;\n' > /tmp/lesson116-helper.c
python3 python/main.py /tmp/lesson116.c > /tmp/lesson116.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson116 /tmp/lesson116.s /tmp/lesson116-helper.c
/tmp/lesson116
echo $?
```

Python emits no g label or data storage, but main loads g through RIP-relative
addressing. GCC compiles the separate helper and links both; exit status is 42.
Tests cover external variables and pointers, omitted data labels, definition
flags, prototypes, historical storage combinations, and the new upstream extern
program. The Python compiler itself never invokes GCC.

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
