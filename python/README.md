# Lesson 73: Character literals

Original chibicc commit: [`aa0accc75e9358d313fef0a6d4005103e2ce25f5`](https://github.com/rui314/chibicc/commit/aa0accc75e9358d313fef0a6d4005103e2ce25f5).
Earlier explanations are available in Git history.

## What changed

The tokenizer converts single-quoted characters into NUM tokens. It reuses the
string escape reader for named, octal, and hexadecimal escapes. Values are
interpreted as signed bytes on this x86-64 target, so '\x80' is -128. Character
literals have int type, not char type. The parser and assembly emitter already
understand numeric nodes and need no change.

This historical reader uses the first byte and searches for the next closing
quote; it does not yet validate multiple-character literals. Thus 'ab' yields
97. Python explicitly maps UTF-8's first byte to a signed value rather than
relying on C's platform-dependent signed char. EOF checks raise CompileError
instead of reading beyond a string buffer.

## Assembly and WSL example

```sh
printf "int main(){return 'a';}\n" > /tmp/lesson73.c
python3 python/main.py /tmp/lesson73.c > /tmp/lesson73.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson73 /tmp/lesson73.s
/tmp/lesson73
echo $?
```

The literal becomes `mov $97, %rax`. Main returns 97, displayed by the shell.
Tests check escaped values, signedness, int sizeof, original token spelling,
malformed input, emitted assembly, executable status, and all original fixtures.

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
