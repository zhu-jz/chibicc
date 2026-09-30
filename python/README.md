# Lesson 43: Line and block comments

Original chibicc commit: [`6c0a42926a10ea5abc781c9db89b105e007512b1`](https://github.com/rui314/chibicc/commit/6c0a42926a10ea5abc781c9db89b105e007512b1).
Earlier explanations are available in Git history.

## What changed

The tokenizer skips `//` through the next newline and `/*` through the first
`*/`. Comments act like whitespace, so `int/*note*/x` still gives two tokens.
Their text stays in the source buffer: diagnostic line numbers and carets keep
pointing at the original file. Strings are read as a unit, so comment markers
inside a string do not start a comment. Block comments do not nest.

An unfinished block comment reports `unclosed block comment` at its opening.
Python also safely accepts an EOF line comment in direct tokenizer calls; the
C file reader normally supplies a final newline before tokenizing.

## Assembly and WSL example

```sh
printf 'int main(){ /* ignored */ return 42; }\n' > /tmp/lesson43.c
python3 python/main.py -o /tmp/lesson43.s /tmp/lesson43.c
cat /tmp/lesson43.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson43 /tmp/lesson43.s
/tmp/lesson43
echo $?
```

The comment emits no instructions. `mov $42, %rax` sets the return value,
then the shared function epilogue restores the stack and returns. The program
prints nothing; `echo $?` immediately afterward displays 42.

Tests run both upstream examples, compare assembly with/without comments,
check markers inside strings and EOF, and check an unclosed comment diagnostic.
All previous compiler features and limits remain at lesson 42's stage.

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
