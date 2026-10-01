# Lesson 160: Quoted includes and source files

Original chibicc commit: [`d367510fcc1396fa252c4b87439c2f9fcd0abbe7`](https://github.com/rui314/chibicc/commit/d367510fcc1396fa252c4b87439c2f9fcd0abbe7).
Earlier explanations are available in Git history.

## What changed

#include "name.h" now reads a file relative to the including file's directory
and inserts its tokens before the remaining input. Included tokens are copied
shallowly, like the original append helper, and their directives are processed
in turn. This supports nested quoted includes. Other include forms remain outside
this commit's grammar.

A File object stores name, file number, and source text. Tokens refer to their
File, diagnostics read the correct source line, and code generation emits every
.file directive plus .loc using each token's file number. Python passes a file
list through the pipeline instead of maintaining C globals. Filename escaping
and the existing UTF-8 diagnostics are preserved; include-open errors also name
the attempted path for clarity.

## Assembly and WSL example

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson160.h
printf '#include "lesson160.h"\nint main(void){return answer();}\n' > /tmp/lesson160.c
python3 python/main.py -S -o /tmp/lesson160.s /tmp/lesson160.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson160 /tmp/lesson160.s
/tmp/lesson160
echo $?
```

.file 1 identifies the C source and .file 2 the header. The header function's
.loc points to file 2; main calls it indirectly and exits with 42. Tests cover
nested relative includes, file numbers, header assembly locations, header lexer
and parser diagnostics, missing/wrong include operands, real execution, and the
original include1/include2 fixtures through the native preprocessing stage.

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
