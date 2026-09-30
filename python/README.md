# Lesson 21: pointer arithmetic and expression types

This educational Python port implements original chibicc commit
[`a6bc4ab101c20b6398fd6bbfe124665bb7db5d25`](https://github.com/rui314/chibicc/commit/a6bc4ab101c20b6398fd6bbfe124665bb7db5d25),
“Make pointer arithmetic work.” Earlier lessons remain in Git history.

## What changed

Pointer addition and subtraction now count elements rather than bytes:

```c
{ x=3; y=5; return *(&x+1); }
```

This returns 5. x is at -16(%rbp), y is at -8(%rbp), and each local slot is
eight bytes. Adding one element to x's address therefore reaches y. The
previous lesson used `&x+8`; that would now advance eight elements.

The supported cases are:

| Operands | Result |
| --- | --- |
| integer + integer, integer - integer | ordinary integer arithmetic |
| pointer + integer, integer + pointer | pointer, with the integer multiplied by 8 |
| pointer - integer | pointer, with the integer multiplied by 8 |
| pointer - pointer | integer element distance: byte difference divided by 8 |
| pointer + pointer, integer - pointer | compile error: invalid operands |

For example, `{x=3; return (&x+2)-&x+3;}` returns 5: advancing two
elements and subtracting the original address produces 2, then adding 3
produces 5.

## Type annotation and tree rewriting

A `Type` contains a kind, `INT` or `PTR`, and an optional `base` type for
pointers. Nodes have an optional `ty` field. The new `python/type.py` module
walks child nodes before assigning the enclosing expression's type.

Numbers and variables are integers. Address-of produces a pointer to its
operand's type. Dereferencing a pointer uses its base type. Comparisons
produce integers. Arithmetic and assignment generally inherit the left
operand's type.

The parser's new `new_add()` and `new_sub()` helpers first annotate their
operands, then rewrite pointer operations:

```text
&x + 1       -> ADD(ADDR(x), MUL(1, 8))
&x - 1       -> SUB(ADDR(x), MUL(1, 8))
(&x+2) - &x  -> DIV(SUB(ADD(ADDR(x), MUL(2, 8)), ADDR(x)), 8)
```

Integer + pointer is rearranged to pointer + integer before scaling.
Pointer subtraction explicitly sets the inner difference's type to integer,
so it does not get interpreted again as pointer arithmetic. Pointer -
integer explicitly retains the pointer type for subsequent operations.
The completed statements are also annotated as their containing block is
parsed.

## Read the assembly

Code generation is unchanged: its existing multiply, add, subtract, and
signed divide instructions handle the rewritten trees. For `*(&x+1)`, the
generator computes `1*8`, saves that result, calculates x's address with
`lea`, adds the saved offset, then loads through the resulting address.

Pointer difference computes a byte difference in `%rax`, then uses the
existing `cqo` and `idiv %rdi` sequence with divisor 8. The result is an
element count. Negative differences therefore work too.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{x=3; y=5; return *(&x+1);}' > /tmp/chibicc-python-lesson21.s
cat /tmp/chibicc-python-lesson21.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson21 /tmp/chibicc-python-lesson21.s
/tmp/chibicc-python-lesson21
echo $?
```

The executable prints nothing; `echo $?` immediately afterward prints **5**.
Use an ordinary interactive shell: `set -e` stops on a nonzero status.

## Current limits, Python/C differences, and tests

This is a small expression type system, not full C type checking. Variables
still have integer type even when assigned addresses: `p=&x; p+1;` performs
ordinary integer addition. Use address expressions such as `&x+1` for the
scaled arithmetic taught here. Dereferencing an integer still receives
integer type, matching upstream's permissive behavior.

All slots and dereference loads remain eight bytes. Accessing neighbouring
locals relies on this compiler's layout; arbitrary memory accesses are
unchecked. Numeric tokens remain limited to 0 through 2147483647.

Python type objects replace C structs and pointers. Type and source metadata
are excluded from structural node equality and checked separately in tests.
Python's Unicode whitespace and character-based diagnostic positions remain.

```sh
python3 python/test.py
```

Tests update the previous byte-offset examples to element offsets, retain
upstream's new negative-offset and pointer-difference examples, and check
integer + pointer, negative differences, chained arithmetic, inferred types,
rewritten trees, invalid operand diagnostics, and earlier executable cases.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
