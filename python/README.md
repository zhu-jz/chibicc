# Lesson 65: Sizeof with type names

Original chibicc commit: [`67543ea113c5cc2b15881e2bbb85ffd44feaef1f`](https://github.com/rui314/chibicc/commit/67543ea113c5cc2b15881e2bbb85ffd44feaef1f).
Earlier explanations are available in Git history.

## What changed

Sizeof now accepts a parenthesized type name as well as an expression:
`sizeof(int)`, `sizeof(int[3][4])`, or `sizeof(int(*)[4])`. A type-name consists
of declaration specifiers followed by an abstract declarator: stars,
parenthesized groupings, and suffixes, but no variable name. It uses the same
two-pass grouping technique as named declarators.

After `sizeof (` the parser uses current scope to decide whether the next
token is a type name. A typedef selects the type branch; a variable hiding
that typedef selects the expression branch. The resulting size is folded
into a NUM node. No variable is allocated and no operand is evaluated.
`sizeof(void)` is 1 here, preserving upstream's GNU-style void-size extension.

Python returns types and token indices instead of C output pointers. The
abstract parser otherwise follows the original grammar. This does not add
casts or change the intermediate long type of numeric expressions and calls.

## Assembly and WSL example

```sh
printf 'int main(){return sizeof(int*[4]);}\n' > /tmp/lesson65.c
python3 python/main.py -o /tmp/lesson65.s /tmp/lesson65.c
cat /tmp/lesson65.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson65 /tmp/lesson65.s
/tmp/lesson65
echo $?
```

The type describes four eight-byte pointers, so its size is 32. The executable
body only moves 32 into `%rax` and returns; the shell displays status 32.
Changing the type to `int(*)[4]` gives one pointer, size 8. Tests cover every
upstream sizeof-type example, typedef/variable ambiguity, void and long long,
nested pointer/array and function-pointer types, missing parentheses and
forbidden typedef storage specifiers. An assembly comparison confirms the
folded constant, and the new sizeof fixture runs with all C fixtures.

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
