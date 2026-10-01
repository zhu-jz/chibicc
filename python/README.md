# Lesson 159: Null preprocessing directives

Original chibicc commit: [`146c7b3dd47bb65da2da86cce7f4d75d8efa157d`](https://github.com/rui314/chibicc/commit/146c7b3dd47bb65da2da86cce7f4d75d8efa157d).
Earlier explanations are available in Git history.

## What changed

Tokens now record at_bol, meaning they are the first non-whitespace token seen on
a line. Preprocessing recognizes # only with that flag. A # followed by the next
line's token is the legal null directive and is removed; other directive text
gets an invalid-preprocessor-directive error at the next token.

Python keeps the original token objects and rewrites their containing list.
Metadata is excluded from token equality, like the existing diagnostic line
number. The scanner matches the original handling of comments: a whole block
comment is skipped without processing its internal newlines for this new flag.
File input is already normalized to end with a newline.

The new original macro.c fixture is compiled directly by our compiler. Other
fixtures still use GCC preprocessing as the original build requires at this step.
This ensures null directives are actually tested by our preprocessing stage.

## Assembly and WSL example

```sh
printf '#\n/* comment */ #\nint main(void){return 42;}\n' > /tmp/lesson159.c
python3 python/main.py -S -o /tmp/lesson159.s /tmp/lesson159.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson159 /tmp/lesson159.s
/tmp/lesson159
echo $?
```

The two null directives disappear before parsing. Assembly still moves 42 into
rax and returns through main's epilogue, giving shell exit status 42. Tests cover
line metadata, whitespace/comments, non-directive # tokens, invalid directives,
emitted assembly, execution, and the directly compiled original macro fixture.

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
