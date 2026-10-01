# Lesson 158: Introduce the preprocessing stage

Original chibicc commit: [`1e1ea39dadd0035443f1d15c651deaf979341879`](https://github.com/rui314/chibicc/commit/1e1ea39dadd0035443f1d15c651deaf979341879).
Earlier explanations are available in Git history.

## What changed

Raw tokenization now leaves keyword spellings as IDENT tokens. The new preprocess
entry point converts those spellings to KEYWORD and returns the same token list.
cc1 runs this stage between tokenization and parsing. No directives or macros
are added in this commit; the compiler's accepted programs and assembly stay the same.

Python moves the existing keyword loop into a named tokenizer helper and adds a
small preprocess.py module. The packaging source list includes that new module.
Tests that inspect parser-ready tokens use the complete pipeline, while the new
stage test checks raw identifiers, conversion, preserved token identities and
numeric values. This corresponds to the original linked-list pass.

## Assembly and WSL example

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson158.c
python3 python/main.py -S -o /tmp/lesson158.s /tmp/lesson158.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson158 /tmp/lesson158.s
/tmp/lesson158
echo $?
```

int and return become keywords before parsing. The generated mov $42, %rax and
main epilogue give shell exit status 42. Tests cover the stage boundary, existing
token snapshots, emitted assembly, packaged execution, and the original C fixtures.

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
