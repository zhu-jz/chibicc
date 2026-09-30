# Lesson 47: Assembly source locations

Original chibicc commit: [`1c91d1943a8ee07034224dd950412c3c87ef3276`](https://github.com/rui314/chibicc/commit/1c91d1943a8ee07034224dd950412c3c87ef3276).
Earlier explanations are available in Git history.

## What changed

Assembly now begins with `.file 1 "filename"`. Before generating each statement
and expression, codegen emits `.loc 1 line_number` using its token's cached
line number. The assembler turns these directives into a debug line table.
A debugger can associate machine instructions with the source file and line;
these directives do not execute and do not change the returned value.

The Python driver still buffers assembly before writing it. It escapes quotes
and backslashes in filenames, an intentional improvement over this upstream
commit's unescaped filename interpolation. Hand-built test nodes without a
source token emit no location directive. Parsed nodes always have tokens.

Instruction snapshots ignore debug directives only; a separate test checks
exact directives for a multiline function and inspects the linked executable's
debug line table with readelf, including a filename containing quotes.

## Assembly and WSL example

```sh
printf 'int main(){\n return 42;\n}\n' > /tmp/lesson47.c
python3 python/main.py -o /tmp/lesson47.s /tmp/lesson47.c
cat /tmp/lesson47.s
gcc -Wl,-z,noexecstack -o /tmp/lesson47 /tmp/lesson47.s
readelf --debug-dump=decodedline /tmp/lesson47
/tmp/lesson47
echo $?
```

`.file` identifies the input and `.loc 1 2` attributes the return expression
to line 2. The instructions still move 42 into `%rax` and return through the
epilogue. The executable prints nothing; the shell displays status 42.
GCC invokes the assembler/linker here; Python remains the C-to-assembly compiler.

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
