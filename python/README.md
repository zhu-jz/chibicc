# Lesson 46: Cached token line numbers

Original chibicc commit: [`6647ad9b843768968db0a331ff7077904c6f58ee`](https://github.com/rui314/chibicc/commit/6647ad9b843768968db0a331ff7077904c6f58ee).
Earlier explanations are available in Git history.

## What changed

After tokenization, one scan assigns a one-based `line_no` to every token,
including EOF. The scan counts newlines inside comments as well as between
tokens. Parsing and code generation pass the offending token into CompileError,
which retains its position and cached line number. The driver uses that number
instead of recounting newlines for a token error.

Lexer failures happen before the completed token list exists, so errors at a
raw character position still count newlines when formatted. Python keeps one
exception class for both cases; passing a Token selects cached metadata, an
integer selects a raw position, and None selects a plain driver error. This
replaces C's separate error_tok/error_at functions. Metadata does not change
token equality in the existing syntax tests.

No language or assembly behavior changes. A missing variable on line 2 still
prints the filename, `:2:`, the source line, and a caret at the name. Tests
verify line numbers through multiline comments, blank lines and EOF, that a
parser exception carries its token's line number, and that a lexer-side error
still displays the correct line.

## WSL example

```sh
printf 'int main(){\n return 42;\n}\n' > /tmp/lesson46.c
python3 python/main.py -o /tmp/lesson46.s /tmp/lesson46.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson46 /tmp/lesson46.s
/tmp/lesson46
echo $?
```

The body still moves 42 into `%rax` and jumps to the epilogue; the shell prints
42 as its exit status. Replacing 42 with `missing` demonstrates the line-2
error. Caching source metadata does not add instructions to the executable.

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
