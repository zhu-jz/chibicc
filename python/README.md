# Lesson 19: source locations on syntax-tree nodes

This educational Python port implements original chibicc commit
[`3d8627719be00e39070eaca0ee5b599f2a877c5c`](https://github.com/rui314/chibicc/commit/3d8627719be00e39070eaca0ee5b599f2a877c5c),
“Add a representative node to each Node to improve error messages.”
Despite the title's wording, the added field is a representative **token**.
Earlier lessons remain in Git history.

## What changed

Code generation can now point to the source of an invalid assignment:

```text
{(a+1)=3;}
   ^ not an lvalue
```

An lvalue names a storage location. A variable is an lvalue, but the result
of adding one to it is a value without its own storage location. Assignment
cannot store into that result. The caret points at `+`, which represents
the left-hand expression, rather than at the assignment's `=`.

This also applies to unreachable code: `{return 1; 1=3;}` is rejected because
the compiler generates every parsed statement, even after a return.

## Parser and error reporting

Every node built by the parser now keeps `tok`, a reference to an existing
`Token`. Numbers and variables keep their own tokens; binary operators keep
their operator token, and negation keeps its minus token. Statements keep
their starting token. A block keeps the first token after its opening brace,
including the closing brace for an empty block, matching upstream.

Parentheses and unary plus do not create nodes, so the enclosed expression
retains its representative token. Rewriting `a>b` as a less-than comparison
with swapped operands also retains the original `>` token.

The generator raises `CompileError(node.tok.position, ...)` for invalid
lvalues, expressions, and statements. The command-line driver prints the
input followed by a caret at that position. Assembly is buffered and printed
only after successful generation, so an error does not leave partial output.

## Assembly and running in WSL

Valid programs emit exactly the same assembly as in lesson 17. For example,
the body of `{return 42;}` still contains:

```asm
  mov $42, %rax
  jmp .L.return
```

The token metadata guides diagnostics; it creates no machine instructions.
The existing prologue saves the frame pointer and reserves local storage;
`.L.return` restores the frame and returns to the C runtime.

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{return 42;}' > /tmp/chibicc-python-lesson19.s
cat /tmp/chibicc-python-lesson19.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson19 /tmp/chibicc-python-lesson19.s
/tmp/chibicc-python-lesson19
echo $?
python3 python/main.py '{(a+1)=3;}'
```

The executable prints nothing; `echo $?` immediately afterward prints **42**.
The final compiler command displays the diagnostic above and exits with 1.
Use an ordinary interactive shell: `set -e` stops on a nonzero status.

## Python/C differences and tests

Python holds a reference to a `Token` object where C stores a token pointer.
The optional field defaults to `None` for manually constructed trees; every
node the parser creates has a token. Source metadata is excluded from
dataclass equality, so structural tree comparisons remain useful; tests
check token identity and positions separately.

Python continues to accept Unicode whitespace and report positions in
characters. Numeric tokens still range from 0 through 2147483647; variables
are implicit and uninitialized before assignment. This step adds no syntax.

```sh
python3 python/test.py
```

Tests check numeric, binary, unary, and rewritten comparison locations,
invalid assignment carets, generator error locations, and the existing
assembly and executable cases.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
