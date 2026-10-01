# Lesson 190: Add variadic macros

Original chibicc commit: [`dc01f94900a9cabf40bb6ec2c5be8b4665c30eda`](https://github.com/rui314/chibicc/commit/dc01f94900a9cabf40bb6ec2c5be8b4665c30eda).
Earlier explanations are available in Git history.

A function-like macro parameter list can now end in `...`. After its fixed
arguments, the reader collects the remaining tokens through the invocation's
closing parenthesis, preserving commas at the outer level. It names that token
sequence `__VA_ARGS__` for ordinary substitution, stringizing or pasting.

Parenthesis depth still protects nested calls. The variadic sequence may be
empty, including when a fixed parameter is supplied without an additional
comma. No special comma removal is introduced. Python reuses its argument
dictionary and adds a boolean field to each macro, matching the original state.

```sh
cat > /tmp/lesson.c <<'C'
#define CALL(...) sum(__VA_ARGS__)
int sum(int x,int y){return x+y;}
int main(void){return CALL(7,35);}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Expansion leaves a real call to sum. Assembly passes values in `%rdi` and
`%rsi`, calls through the function address in `%rax`, and returns its result.
Tests cover empty sequences, variadic-only and mixed parameter lists, forwarding
commas, nested calls, stringizing and an ellipsis in the wrong position.

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
