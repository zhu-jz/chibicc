# Lesson 5: multiplication, division, and parentheses

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`84cfcaf98f3d19c8f0f316e22a61725ad201f0f6`](https://github.com/rui314/chibicc/commit/84cfcaf98f3d19c8f0f316e22a61725ad201f0f6),
“Add *, / and ().” Original C files remain intact on the `python-lessons`
branch. Previous lessons and their explanations remain in Git history:

| Lesson | Original commit | Python commit |
| --- | --- | --- |
| 1: one integer | `0522e2d` | `77c10f9` |
| 2: addition and subtraction | `bf7081f` | `d74a628` |
| 3: tokenization | `a1ab0ff` | `b92e285` |
| 4: error locations | `cc5a6d9` | `533dbf3` |

## Why an expression tree?

The previous compiler emitted each addition or subtraction as it read it.
That is insufficient for `5+6*7`: multiplication must happen before the
addition, giving 47. Parentheses can change grouping: `(5+6)*7` gives 77.

We now have three stages:

```text
source characters → tokens → expression tree → assembly
```

A tree node is either a number or an operator with left and right children.
For `5+6*7`, the tree is:

```text
    +
   / \
  5   *
     / \
    6   7
```

The tree records grouping, not a precomputed answer. Python never evaluates
the arithmetic: the generated executable performs it.

## Read the parser

The three parser functions follow this grammar:

```text
expr    = mul (("+" | "-") mul)*
mul     = primary (("*" | "/") primary)*
primary = "(" expr ")" | number
```

Outside quotes, `*` means repetition and `|` means a choice. Each Python
function returns `(node, next_token_index)`. This replaces C's returned
node plus the `Token **rest` output parameter.

- `primary()` reads a number, or recursively calls `expr()` inside a pair
  of parentheses. Parentheses control grouping and need no node of their own.
- `mul()` combines primary expressions using multiplication and division.
- `expr()` combines whole multiplication/division expressions using addition
  and subtraction. This gives multiplication and division higher precedence.

Both loops put the previous tree on the left of each new operator. Thus
`10-3-2` groups as `(10-3)-2`, and `20/2/2` as `(20/2)/2`. After parsing,
`main()` requires EOF; leftover tokens produce `extra token`.

Tokenization now recognizes all ASCII punctuation, like C's `ispunct`.
The parser still accepts only the operators in this grammar. For example,
`1@2` becomes valid tokens but fails parsing with `extra token`.
Letters still fail tokenization with `invalid token`.

## Read the assembly generator

`CodeGenerator.gen_expr()` follows the original commit's strategy:

1. Generate the right child, leaving its result in `%rax`.
2. `push %rax` saves that result on the stack.
3. Generate the left child, leaving its result in `%rax`.
4. `pop %rdi` restores the right result into `%rdi`.
5. Perform the operation with left in `%rax` and right in `%rdi`.

Saving the right value is necessary because evaluating the left subtree
may itself overwrite registers. The stack supports nested expressions.
Right-first evaluation does not reverse the operands: `sub %rdi, %rax`
still computes left minus right. Tree grouping and evaluation order are
different concepts.

For `5+6*7`, the exact output is:

```asm
  .globl main
main:
  mov $7, %rax
  push %rax
  mov $6, %rax
  pop %rdi
  imul %rdi, %rax
  push %rax
  mov $5, %rax
  pop %rdi
  add %rdi, %rax
  ret
```

`.globl main` exposes the function to the linker, and `main:` labels its
entry. In AT&T syntax the source comes first: `$7` is a constant and `%rax`
is a register. `imul` produces 42, the stack saves it while `mov` loads 5,
and `add` produces 47.

Each push of a 64-bit register decreases `%rsp` by eight bytes; pop restores
those bytes and increases `%rsp` again. The generator tracks a temporary
stack depth and asserts it is zero at the end, just as C does. Balanced
pushes and pops leave the caller's return address in place for `ret`.
The generated function makes no calls and needs no stack-frame prologue.

Division emits:

```asm
  cqo
  idiv %rdi
```

`cqo` sign-extends the left operand in `%rax` into the 128-bit dividend
`%rdx:%rax`. `idiv` divides that signed dividend by `%rdi`, leaving the
quotient in `%rax` and remainder in `%rdx`. The quotient truncates toward
zero: `(0-7)/2` gives -3, unlike Python's floor division `-7 // 2`, which
gives -4. We use the machine instruction, not Python division.

As in the original, division by zero is not checked by the compiler; the
executable faults if it executes such a division. There is no constant
folding or runtime error handler in this lesson.

## Run it in WSL

Use x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu). From the repository root, run these commands individually:

```sh
python3 python/main.py '5+6*7' > /tmp/chibicc-python-lesson5.s
cat /tmp/chibicc-python-lesson5.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson5 /tmp/chibicc-python-lesson5.s
/tmp/chibicc-python-lesson5
echo $?
```

The shell's `echo` prints **47**; the executable itself prints nothing.
Run `echo $?` immediately after the executable. `ret` returns to the C
runtime; an `int` result uses `%eax`, the low 32 bits of `%rax`, and Linux
exposes the low eight bits as the exit status. Thus -3 is displayed as 253.
Use an ordinary interactive shell; `set -e` would stop a script on a
nonzero exit status. The compiler's own success status is 0.

GCC assembles and links our assembly with the C runtime. `-static` follows
the original tests. `-Wl,-z,noexecstack` marks the stack non-executable.
No original C compiler code or Python `eval()` is invoked by our compiler.

## Errors, scope, and Python/C differences

Your previous example `18 11` now reports:

```text
18 11
   ^ extra token
```

An incomplete expression reports `expected an expression`, and a missing
closing parenthesis reports `expected ')'`. Caret diagnostics are retained.
Unary signs are still unsupported: `-1`, `+42`, and `1--2` remain errors.
Negative results can be written using subtraction, such as `0-1`.

Python uses dataclass nodes and a list of tokens; C uses allocated structs
and a linked list. The generator's assembly list and stack depth are
instance attributes rather than C's printed output and global depth.
Errors carry positions in exceptions, and assembly is printed only after
successful compilation. Token positions count Unicode characters instead
of C byte offsets; tabs, wide characters, and newlines can visually misalign
this basic caret display. Python also accepts Unicode whitespace.

We retain the explicit literal range 0 through 2147483647, matching the
nonnegative representable values of C's 32-bit node value. C does not check
its numeric conversion. This lesson uses register-to-register arithmetic,
so the earlier immediate-operand restriction is no longer the reason for
the limit. Intermediate arithmetic uses 64-bit registers. Extremely deep
or long expression trees can hit Python's recursion limit; we do not add
a separate iterative traversal or resource-limit system in this lesson.

## Tests and stopping point

```sh
python3 python/test.py
```

Tests check tree shapes for precedence and left associativity, exact
assembly for representative operations, and balanced temporary stack depth.
They assemble and execute 35 expressions, including all seven upstream
tests, all previous valid cases, nested parentheses, operand order,
truncation toward zero, negative divisors, and 64-bit intermediate results.
Additional tests check token positions, unsupported syntax, and exact
caret diagnostics. Artifacts use automatically cleaned temporary directories.

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full notice
remains in `LICENSE` here and in the repository root. This port uses the
same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
