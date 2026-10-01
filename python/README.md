# Lesson 178: Add macro token pasting

Original chibicc commit: [`8f561aed9b7a47c38afd8c1cc75bc9a700ae97b5`](https://github.com/rui314/chibicc/commit/8f561aed9b7a47c38afd8c1cc75bc9a700ae97b5).
Earlier explanations are available in Git history.

In function-like replacement bodies, `##` joins the neighboring token texts
and tokenizes the result. Exactly one resulting token is required. It can form
numbers, operators or identifiers. Pasting uses unexpanded argument tokens;
a multi-token left argument supplies its last token, while a right argument
supplies its first token. Remaining tokens retain their order.

Empty arguments contribute no token and leave the other side intact. Pasted
results are rescanned for macros. Invalid results and a pasting operator at
an expansion's start or end are diagnosed. As in this original commit,
object-like bodies do not run the substitution helper, so pasting is currently
handled only in function-like macros. Python also diagnoses an empty argument
followed by a trailing operator instead of following a null token pointer.

```sh
printf '#define PASTE(x,y) x##y\nint main(void){int answer42=42;return PASTE(answer,42);}\n' > /tmp/lesson.c
python3 python/main.py -E /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The pasted identifier refers to a local variable. Assembly loads that stack
slot into `%rax` and returns. Tests cover decimal and hexadecimal numbers,
identifiers, empty arguments, raw multi-token arguments, chained pastes and
invalid operators. The upstream fixture is copied without edits.

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
