# Lesson 20: address-of and dereference

This educational Python port implements original chibicc commit
[`863e2b8de25fdf43a4a63b93d0f57718e9edaa47`](https://github.com/rui314/chibicc/commit/863e2b8de25fdf43a4a63b93d0f57718e9edaa47),
“Add unary & and *.” Earlier lessons remain in Git history.

## What changed

`&x` produces the address of variable `x`; `*p` reads the eight-byte value
at the address stored in `p`. A dereference can also be an assignment target:

```c
{ x=3; p=&x; *p=5; return x; }
```

This returns 5 because `p` points at `x`'s stack slot. Chaining dereferences
works too: `{x=3; p=&x; q=&p; return **q;}` returns 3.

These are still untyped, eight-byte values. Address arithmetic counts bytes,
so upstream uses `*(&x+8)` to access the next local slot. For
`{x=3; y=5; return *(&x+8);}`, the local layout is:

```text
%rbp -  8: y = 5
%rbp - 16: x = 3
```

Variables are stored in reverse order of first encounter, as before. Adding
8 to x's address therefore reaches y. This example relies on this compiler's
specific stack layout; it is not a general guarantee of C.

## Parser and lvalues

The unary grammar becomes:

```text
unary = ("+" | "-" | "*" | "&") unary | primary
```

Recursive parsing gives prefix operators higher precedence than multiplication
and permits combinations such as `*&x` and `**q`. The surrounding grammar
distinguishes multiplication from dereference: `1**p` means `1 * (*p)`.

The parser builds `ADDR` and `DEREF` nodes. To evaluate `ADDR`, code generation
asks for the operand's address. To evaluate `DEREF`, it evaluates the operand
to obtain an address and then loads from it.

`gen_addr()` now accepts both variables and dereferences. For a variable,
it calculates the address of its stack slot. For `*p`, it evaluates `p`
without loading through that pointer again: that result is already the
address where an assignment must store. Expressions such as `&1` and
`&(x+1)` still report “not an lvalue.”

## Read the assembly

With x at -16 and p at -8, `&x` emits:

```asm
  lea -16(%rbp), %rax
```

`lea` calculates an address without reading memory. Reading `*p` emits:

```asm
  lea -8(%rbp), %rax
  mov (%rax), %rax
  mov (%rax), %rax
```

The first load reads p's stored address; the second reads x's value.
For `*p=5`, the generator instead saves p's address value on the temporary
stack, evaluates 5, restores the address into `%rdi`, and emits
`mov %rax, (%rdi)`. The existing assignment generator already performs this
store; only address calculation needed extending.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{x=3; p=&x; *p=5; return x;}' > /tmp/chibicc-python-lesson20.s
cat /tmp/chibicc-python-lesson20.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson20 /tmp/chibicc-python-lesson20.s
/tmp/chibicc-python-lesson20
echo $?
```

The executable prints nothing; `echo $?` immediately afterward prints **5**.
Use an ordinary interactive shell: `set -e` stops on a nonzero status.

## Python/C differences and tests

Python creates syntax-tree objects and assembly text. The emitted executable
performs the actual memory accesses; Python does not simulate pointers.
All locals and loads/stores remain eight bytes, matching upstream. Invalid
addresses are unchecked. Existing Unicode whitespace, character positions,
and checked decimal-token range differences remain unchanged.

Python parser functions return `(node, next_index)` tuples instead of using
C output pointers for the remaining tokens. Source tokens stay on the new
nodes for diagnostics.

```sh
python3 python/test.py
```

Tests include all seven new upstream examples, pointer chains, stores through
dereferences, `&*p`, multiplication next to dereference, exact address/load
assembly, and invalid address-of operands. Earlier tests remain in place.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
