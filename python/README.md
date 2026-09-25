# Lesson 11: names and allocated local-variable slots

This educational Python port implements original chibicc commit
[`482c26b536f8e5c998af6210470cd3d97a47ee9a`](https://github.com/rui314/chibicc/commit/482c26b536f8e5c998af6210470cd3d97a47ee9a),
“Support multi-letter local variables.” Earlier lessons remain in Git
history; lesson 10 is Python commit `b542a70`.

## What changed

Names can now contain more than one letter:

```text
foo=3; foo;                      → 3
foo123=3; bar=5; foo123+bar;      → 8
Total=3; total=7; Total+total;    → 10
_value1=5; _value1;              → 5
```

The first character must be an ASCII letter or underscore. Later characters
can also be digits. Names are case-sensitive; `foo` and `foo123` are distinct,
as are `Total` and `total`. Declarations are still unnecessary. A name is
registered the first time it appears, whether read or assigned. Reading
before assignment still gives an unspecified value from its stack slot.

Previously the compiler reserved 208 bytes for `a` through `z`. It now
reserves space for the names actually encountered, rounded up to a multiple
of 16 bytes. It is no longer limited to 26 variables.

## Tokenization and shared objects

`is_ident1()` in `tokenizer.py` checks the first character and `is_ident2()`
checks later characters. The scanner consumes the complete name into one
`IDENT` token. `abc` now forms one token; the previous lesson produced three.

`common.py` adds two dataclasses:

- `Obj` stores a local variable's name and stack offset.
- `Function` stores the statement list, the local-variable list, and the
  stack size. It describes the single generated `main` function; this
  lesson does not introduce function-definition syntax.

A variable tree node now refers to an `Obj` through its `var` field.
For `foo=3; foo+foo;`, all three occurrences point to the same object.
Code generation can assign that object's offset once, and every reference
will use it.

`parse.py` groups its parsing functions in a `Parser` class. The instance
holds the tokens and local-variable list for one compilation. `find_var()`
searches for an exact name. If none exists, `primary()` creates an `Obj`
and inserts it at the front of the list, matching C's linked-list order.
The grammar and precedence rules are unchanged.

The public `parse(tokens)` function now returns a `Function` instead of a
statement list. `main.py` passes this object to `codegen()`.

## Stack allocation

Code generation first walks the local-variable list, assigning successive
eight-byte slots at offsets -8, -16, -24, and so on from `%rbp`. Because
new names are added at the front, allocation order is the reverse of first
appearance in the source. For `foo=3; bar=5; foo+bar;`:

| Variable | Offset from `%rbp` |
| --- | --- |
| `bar` | -8 |
| `foo` | -16 |

The total slot size is rounded up using integer arithmetic:

```python
program.stack_size = (offset + 15) // 16 * 16
```

Zero variables need 0 bytes; one or two need 16; three or four need 32.
This follows the original commit's 16-byte alignment policy. The generated
function still saves `%rbp` before reserving local storage, and restores
the caller's frame pointer at the end.

`gen_addr()` now reads the saved offset rather than calculating it from a
letter. To get `foo`'s address in the two-variable example, it emits:

```asm
  lea -16(%rbp), %rax
```

`lea` computes an address. `mov (%rax), %rax` reads the eight-byte value
there. Assignments still save the destination address, compute the right
side, and store using `mov %rax, (%rdi)`.

## Run it in WSL

Use Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu). From the repository root:

```sh
python3 python/main.py 'foo=3; bar=5; foo+bar;' > /tmp/chibicc-python-lesson11.s
cat /tmp/chibicc-python-lesson11.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson11 /tmp/chibicc-python-lesson11.s
/tmp/chibicc-python-lesson11
echo $?
```

The last command prints **8**. Quote the source so the shell does not
interpret its semicolons. The executable prints nothing; `echo $?`
immediately afterward displays its exit status. Use an ordinary interactive
shell: `set -e` would stop a script on status 8.

The prologue now reserves only 16 bytes for this example:

```asm
  .globl main
main:
  push %rbp
  mov %rsp, %rbp
  sub $16, %rsp
```

The body stores 3 in `foo` and 5 in `bar`, then loads and adds them. The
result remains in `%rax`. The epilogue restores the stack:

```asm
  mov %rbp, %rsp
  pop %rbp
  ret
```

GCC assembles and links the emitted code with the C runtime. `-static`
follows upstream tests and `-Wl,-z,noexecstack` marks the stack
non-executable. Python performs compilation without `eval()` or invoking
the original C compiler. The compiler's own successful exit status is 0.

## Intentional differences and tests

Python uses lists and shared dataclass objects instead of C linked lists
and pointers. The new `Parser` instance keeps locals separate for repeated
calls to `parse()`; the C implementation accumulates locals in a global
list during its single command-line compilation. We preserve its order
and exact-name lookup. Python's `//` is needed for the alignment calculation
because `/` would produce a floating-point value; positive integer division
in the C expression produces an integer.

Existing differences remain: explicit numeric-token bounds of 0 through
2147483647, Unicode whitespace support, character-based diagnostic offsets,
and assembly buffered until compilation succeeds. Identifiers deliberately
use ASCII rules, matching upstream. Variables and arithmetic intermediates
use 64 bits; normal exit statuses expose only eight bits. Uninitialized
variables and empty-program results remain unspecified, deep expression
trees can reach Python's recursion limit, and runtime division by zero
remains unchecked.

```sh
python3 python/test.py
```

Tests retain earlier cases and cover every upstream test case through this
commit. They check complete identifier tokens, exact names and case,
shared object identity, independent parser instances, reverse allocation
order, 0/16/32-byte stack sizes, exact assembly, and executable results for
more than 26 locals. Temporary build artifacts are cleaned up automatically.

The implementation remains in `python/` on `python-lessons`; the original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in `LICENSE` here and in the repository
root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
