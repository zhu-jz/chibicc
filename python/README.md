# Lesson 162: Preprocess-only output with -E

Original chibicc commit: [`d138864a2a99849e43d81ca071b7a799edc0e65a`](https://github.com/rui314/chibicc/commit/d138864a2a99849e43d81ca071b7a799edc0e65a).
Earlier explanations are available in Git history.

## What changed

-E runs tokenization and preprocessing, prints each surviving token's original
spelling, and stops before parsing. Each token receives a leading space; tokens
marked at_bol start a new output line after the first token. A final newline is
always printed, including empty input. Output goes to stdout or the global -o
path. A single output path is rejected with multiple inputs in stopping modes.

The same original commit permits absolute quoted include filenames, rather than
always adding the including directory. Python builds token text with a list and
join and uses the existing output writer. Input that is lexically valid but not
valid C grammar can still be printed with -E, because the parser is not called.
The include-warning loop behavior from the preceding commit remains in effect.

## Assembly and WSL example

```sh
printf 'int answer(void){return 42;}\n' > /tmp/lesson162.h
printf '#include "lesson162.h"\nint main(void){return answer();}\n' > /tmp/lesson162.c
python3 python/main.py -E -o /tmp/lesson162-pp.c /tmp/lesson162.c
python3 python/main.py -S -o /tmp/lesson162.s /tmp/lesson162-pp.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson162 /tmp/lesson162.s
/tmp/lesson162
echo $?
```

The preprocessing output contains both function definitions with spaced tokens.
Compiling that text emits an indirect call to answer and returns 42, visible as
the shell exit status. Tests check exact spacing/newlines, stdout and -o, absolute
includes, empty and unparsed input, original number spelling, output re-compilation,
multiple-input rejection, execution, and the original fixtures.

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
