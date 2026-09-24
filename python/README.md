# Lesson 10: single-letter local variables

This educational Python port implements original chibicc commit
[`1f9f3adf324af1432a380b41c7690834e649e346`](https://github.com/rui314/chibicc/commit/1f9f3adf324af1432a380b41c7690834e649e346),
“Support single-letter local variables.” Earlier lessons remain in Git
history; lesson 9 is Python commit `f2b5136`.

## What changed

You can assign values to lowercase letters `a` through `z` and read them:

```text
a=3; a;           → 3
a=3; z=5; a+z;    → 8
a=b=3; a+b;       → 6
```

Every statement still ends with `;`. No declarations are needed at this
stage. Each letter has its own eight-byte stack slot. There are 26 slots,
so the generated function reserves 26 × 8 = 208 bytes.

## Tokenization and parsing

`tokenizer.py` recognizes each lowercase ASCII letter as an `IDENT` token.
`abc` becomes three identifier tokens, not one name, and uppercase letters
remain invalid. `primary()` in `parse.py` turns an identifier into a
`Node("VAR", name=letter)`.

Assignment becomes the lowest-precedence expression operation:

```text
expr   = assign
assign = equality ("=" assign)?
```

The `?` means optional. The recursive call on the right makes `a=b=3`
group as `a=(b=3)`: store 3 in `b`, then store the same result in `a`.
The result of assignment is the value stored, so `(a=7)+2;` yields 9.
Equality still uses `==`: `a=5==5;` assigns the comparison result 1 to `a`.

An assignment's left side must identify a storage location. Such an
expression is called an *lvalue*. A variable, including a parenthesized
variable such as `(a)`, works. `1=3;` and `(a+1)=3;` report `not an lvalue`.
As in the original commit, that check occurs in code generation and the
message has no source caret. The Python exception uses `position=None`
for this plain diagnostic; ordinary source errors retain their carets.

## Stack slots, addresses, and values

The new function prologue is:

```asm
  push %rbp
  mov %rsp, %rbp
  sub $208, %rsp
```

It saves the caller's frame pointer, establishes `%rbp` as a stable base,
and moves `%rsp` down to reserve local-variable space. Variable addresses
are calculated from `%rbp`:

```text
%rbp          saved caller frame pointer
%rbp - 8      a
%rbp - 16     b
...
%rbp - 208    z  ← %rsp after allocation
below this    temporary expression pushes
```

`gen_addr()` computes a variable's address using
`(ord(name) - ord('a') + 1) * 8`. For `a`, it emits:

```asm
  lea -8(%rbp), %rax
```

`lea` computes the address; it does not read the stored value. Reading `a`
then emits `mov (%rax), %rax`, which loads eight bytes from that address.
The parentheses mean access memory at the address in the register.

To compile `a=3; a;`, the body is:

```asm
  lea -8(%rbp), %rax
  push %rax
  mov $3, %rax
  pop %rdi
  mov %rax, (%rdi)
  lea -8(%rbp), %rax
  mov (%rax), %rax
```

The assignment saves the destination address on the stack, evaluates the
right side into `%rax`, restores the address into `%rdi`, and stores the
value there. The store leaves `%rax` holding 3, which makes chained
assignment work. The final two instructions read `a` back.

The epilogue restores the stack and caller's frame pointer:

```asm
  mov %rbp, %rsp
  pop %rbp
  ret
```

The generator still checks that temporary pushes and pops balance after
each statement. The prologue's saved `%rbp` and reserved local storage are
separate from that temporary depth counter.

## Run it in WSL

With Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py 'a=3; z=5; a+z;' > /tmp/chibicc-python-lesson10.s
cat /tmp/chibicc-python-lesson10.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson10 /tmp/chibicc-python-lesson10.s
/tmp/chibicc-python-lesson10
echo $?
```

The final command prints **8**. The generated program itself prints
nothing; `echo $?` immediately afterward shows its exit status. Quote the
source to protect semicolons and operators from the shell. Use an ordinary
interactive shell; `set -e` would stop a script on status 8.

Python emits assembly without `eval()` or invoking the original C compiler.
GCC assembles and links it with the C runtime. `-static` follows the original
tests; `-Wl,-z,noexecstack` marks the stack non-executable. A successful
compiler invocation returns status 0 independently of the generated result.

## Behavior and intentional Python/C differences

Variables are not initialized automatically. Reading `a;` before assigning
it reads whatever bytes occupy its stack slot; tests do not assume a value
for that case. Empty programs likewise leave the result unspecified.
The final statement still determines the returned value in this early
compiler. The exit status retains only its low eight bits.

The existing generator evaluates ordinary binary tree nodes right child
first. Assignment computes the destination address before its right side.
For `>` and `>=`, the parser still swaps tree children to use `<` and `<=`.
With assignments nested inside expressions, that ordering can be observable;
it follows this original compiler and is not a promise about general C
expression evaluation order.

Python uses dataclasses and lists instead of C structs and linked lists,
and `ord()` instead of arithmetic on C character values. The stack layout
and emitted load/store instructions follow the original commit. Numeric
tokens remain limited to 0 through 2147483647; intermediate values and
variable slots are 64-bit. This explicit literal check differs from C's
unchecked conversion. Unicode whitespace, character-based error positions,
and buffered assembly output remain intentional Python differences.
Deep trees can hit Python's recursion limit; runtime division by zero
remains unchecked.

## Tests and attribution

```sh
python3 python/test.py
```

Tests retain the earlier expression cases and all 30 original assertions
through this commit. They check identifier tokens, assignment tree shape,
exact address/load/store assembly, the new prologue and epilogue, repeated
assignment, chained assignment, signed values, and all 26 distinct stack
slots. Invalid assignment targets and missing operands have diagnostic
checks. Temporary assembly and executable files are cleaned up automatically.

The implementation lives under `python/` on the `python-lessons` branch;
original C files remain intact. Original chibicc: Copyright (c) 2019 Rui
Ueyama, MIT licensed. The full notice remains in `LICENSE` here and at the
repository root, and this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
