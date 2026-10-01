# Lesson 183: Support backslash-newline continuation

Original chibicc commit: [`b33fe0ea828e6a8ff3ec2d8bd5845da2b337afa5`](https://github.com/rui314/chibicc/commit/b33fe0ea828e6a8ff3ec2d8bd5845da2b337afa5).
Earlier explanations are available in Git history.

Reading a source file now removes each backslash followed immediately by a
newline before tokenization. This can join identifiers, continue macro bodies,
or extend a line comment. It also applies inside string literals because the
transformation precedes lexical interpretation.

A counter delays each removed newline until the next ordinary newline, where
it adds blank lines. Later source lines therefore retain their physical line
numbers. Tokens within a continued logical line use its opening line number,
matching the original approach. Python constructs a new string rather than
moving characters within a mutable C buffer. Raw in-memory tokenizer calls
remain untransformed; file and stdin compilation use the new reading stage.

```sh
cat > /tmp/lesson.c <<'C'
#define VALUE 7+\
35
int main(void){return VALUE;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The replacement is the token expression `7+35`; assembly adds those values
and returns 42 in `%rax`. Tests cover joined identifiers, macros, strings,
continued comments, delayed newline counts and a later line's diagnostic.

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
