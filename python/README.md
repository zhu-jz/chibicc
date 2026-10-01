# Lesson 245: Align diagnostic carets with displayed Unicode text

Original chibicc commit: [`37998be0c183508e54f10f57d63d87e6e7eb0607`](https://github.com/rui314/chibicc/commit/37998be0c183508e54f10f57d63d87e6e7eb0607).
Earlier explanations are available in Git history.

Diagnostics now measure the displayed columns before an error. The original
Unicode tables assign zero columns to combining and control characters, two
to selected East Asian and emoji ranges, and one to other characters. Counting
UTF-8 bytes or Python characters alone can put a caret under the wrong column.

```sh
printf 'int main(void){int 漢字=42;return 漢字;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly stores and reloads 42 exactly as for an ASCII local name; local names
do not affect machine instructions. The new tests also provoke an undefined
identifier after wide and combining characters and check the caret column.
Python sums widths over Unicode characters; C decodes UTF-8 bytes while scanning.
We preserve the original fixed range tables rather than using the host Python
Unicode database. Their control-character width, including tabs, is zero;
terminal tab expansion is not modeled by this original commit.

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
