# Lesson 193: Concatenate adjacent string literals

Original chibicc commit: [`ab4f1e1e197ecae40299b99dc00b1c92a4a3cb28`](https://github.com/rui314/chibicc/commit/ab4f1e1e197ecae40299b99dc00b1c92a4a3cb28).
Earlier explanations are available in Git history.

After macro expansion and keyword conversion, each consecutive run of string
tokens becomes one character array. Their already-decoded bytes are joined,
removing the intermediate terminating zeros and retaining one final zero.
Embedded zeros remain part of the data. Whitespace and comments do not stop
a run, and strings produced by macros participate too.

Python bytes concatenation replaces the C buffer allocation and memcpy loop.
The first token retains its source spelling and location, matching this original
commit. Consequently, its early `-E` printer displays only the first spelling
of a joined run; compilation uses the complete decoded data and array type.
This historical output limitation is tested rather than silently changed.

```sh
printf 'int main(void){return sizeof("abc" "def");}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 7, six characters plus the terminating zero
```

sizeof becomes an integer constant, so assembly loads 7 into `%rax` and returns.
A string subscript instead computes an address and loads a character from static
data. Tests check array size, indexing, embedded zeros, comments, macro-produced
strings, separately decoded hexadecimal escapes and the original output behavior.

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
