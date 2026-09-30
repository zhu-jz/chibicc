# Lesson 22: declared integer and pointer variables

This educational Python port implements original chibicc commit
[`b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb`](https://github.com/rui314/chibicc/commit/b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb),
“Add keyword "int" and make variable definition mandatory.”
Earlier lessons remain in Git history.

## What changed

Variables must now be declared before use:

```c
{ int x; x=3; return x; }
{ int x=3; return x; }
{ int x=3, y=5; return x+y; }
```

The first two return 3; the last returns 8. The old `{x=3; return x;}`
now reports “undefined variable” at the first x.

A declaration supplies each variable's type. Prefix stars create pointers:

```c
{ int x=3; int *p=&x; int **q=&p; return **q; }
```

This returns 3. p points to an integer, and q points to a pointer to an
integer. Each declarator starts from the base type independently:
in `int *p, x;`, p is a pointer and x is an integer.

Pointer variables now participate in scaled arithmetic:

```c
{ int x=3; int y=5; int *p=&x; return *(p+1); }
```

This returns 5. Unlike the previous lesson's implicitly integer variables,
p carries a pointer type, so adding 1 advances eight bytes.

Dereferencing an integer is now rejected at the `*` token:
`{return *1;}` reports “invalid pointer dereference.”

## Parser and initialization

The block grammar now accepts declarations as well as statements:

```text
declspec = "int"
declarator = "*"* identifier
declaration = declspec (declarator ("=" assign)?
                       ("," declarator ("=" assign)?)*)? ";"
compound-stmt = (declaration | stmt)* "}"
```

`declspec()` reads the base type. `declarator()` reads any stars and the
name. `declaration()` creates a typed local object, then optionally parses
an initializer. The local is registered before parsing its initializer,
and later names in the same declaration can refer to earlier ones.

Initializers become ordinary assignment expression statements inside a
`BLOCK` node. Thus `int x=3;` reuses the same store instructions as
`x=3;`. A declaration without an initializer creates storage but emits no
initialization. `int;` is accepted as an empty declaration, matching upstream.

A variable reference now looks up an existing local and fails if none exists.
Type annotation reads each variable's declared type instead of assuming INT.

## Read the assembly

For `{int x=3; int *p=&x; *p=5; return x;}`, p is at -8(%rbp) and x at
-16(%rbp). Both slots remain eight bytes, including `int` in this lesson.

The declaration `int *p=&x;` generates this store:

```asm
  lea -8(%rbp), %rax
  push %rax
  lea -16(%rbp), %rax
  pop %rdi
  mov %rax, (%rdi)
```

The first address is p's destination slot; the second is x's address.
The temporary stack preserves the destination while evaluating the
initializer. The final `mov` stores x's address into p. Declaration syntax
and type checks happen during compilation; no new code generator is needed.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{int x=3; int *p=&x; *p=5; return x;}' > /tmp/chibicc-python-lesson22.s
cat /tmp/chibicc-python-lesson22.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson22 /tmp/chibicc-python-lesson22.s
/tmp/chibicc-python-lesson22
echo $?
```

The executable prints nothing; `echo $?` immediately afterward prints **5**.
Use an ordinary interactive shell: `set -e` stops on a nonzero status.

## Current limits and Python/C differences

Declarations are recognized inside blocks. They are not accepted directly
as an if/while body or in a for initializer; use a block or declare the
variable before the loop. Only int and pointers are supported.

Locals still share one function-wide list. A name declared inside a nested
block remains visible afterward, and a later redeclaration hides the older
object for subsequent references. This follows the current original commit,
which has no block scope yet. Uninitialized locals and arbitrary pointer
accesses remain unchecked. Assignment type compatibility is also unchecked.

The original C declarator writes a name into a type object, including its
shared integer type. Python creates a separate outer type object for each
declarator, preserving its name without mutating the shared integer type.
This intentional metadata difference does not change generated assembly.

Python uses lists, dataclasses, tuples, and `None` in place of C lists,
structs, output pointers, and null pointers. Unicode whitespace and
character-based diagnostic positions remain. Decimal tokens still range
from 0 through 2147483647. Process exit statuses retain only eight bits.

## Tests

```sh
python3 python/test.py
```

The suite includes every current upstream executable example and earlier
arithmetic/control-flow regressions updated to explicit declarations. It
checks comma-separated declarations, initialization order, pointer chains,
scaled arithmetic on pointer variables, local layout, empty declarations,
current name visibility, keyword boundaries, invalid declarations, undefined
variables, invalid dereferences, exact assembly, and diagnostic carets.
Executables run with a timeout; temporary assembly and binaries are cleaned up.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
