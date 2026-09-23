# Lesson 7: equality and relational comparisons

This educational Python port follows Rui Ueyama's
[chibicc](https://github.com/rui314/chibicc), one original commit at a time.
This lesson implements original commit
[`25b4b85b887c643e337a9fbcd1b0220b413952bf`](https://github.com/rui314/chibicc/commit/25b4b85b887c643e337a9fbcd1b0220b413952bf),
“Add ==, !=, <= and >= operators.” The commit also implements `<` and `>`.
The `python-lessons` branch retains the original C files unchanged. Earlier
Python lessons and their explanations remain in Git history, ending with
lesson 6 at Python commit `1bb6952`.

## What changed

The compiler now accepts six comparisons. Each returns **1** when true or
**0** when false:

| Operator | Meaning | Example and result |
| --- | --- | --- |
| `==` | equal | `42==42` → 1 |
| `!=` | not equal | `42!=42` → 0 |
| `<` | less than | `0<1` → 1 |
| `<=` | less than or equal | `1<=1` → 1 |
| `>` | greater than | `1>2` → 0 |
| `>=` | greater than or equal | `1>=1` → 1 |

The shell uses `<` and `>` for redirection, so quote comparison expressions
when passing them as command-line arguments.

## How the tokenizer and parser work

The tokenizer checks `==`, `!=`, `<=`, and `>=` before trying a single
punctuation character. For `1<=2`, it produces `NUM(1), PUNCT(<=), NUM(2),
EOF`. Each token retains its source position for caret diagnostics. Other
punctuation still forms one-character tokens; the parser rejects syntax it
does not support.

The parser now has two more precedence levels:

```text
expr       = equality
equality   = relational (("==" | "!=") relational)*
relational = add (("<" | "<=" | ">" | ">=") add)*
add        = mul (("+" | "-") mul)*
mul        = unary (("*" | "/") unary)*
unary      = ("+" | "-") unary | primary
primary    = "(" expr ")" | number
```

Outside quotes, `*` means repetition and `|` means a choice. A parser
function returns a tree node and the next unconsumed token index. Lower
lines bind more tightly: `5+6*7==47` groups as `(5+(6*7))==47`. Relational
operators bind more tightly than equality: `3<4==1` means `(3<4)==1`.
The loops group repeated operators from left to right, so `1<2<3` means
`(1<2)<3`; the first comparison produces 1, then `1<3` produces 1.

The tree has equality nodes `==` and `!=`, and relational nodes `<` and
`<=`. For `a>b`, the parser constructs `b<a`; for `a>=b`, it constructs
`b<=a`. This follows the original C code and lets code generation reuse
two relational operations. These programs have no side effects, so swapping
tree operands does not change their result. For `1>2`, the tree is `<` with
2 on the left and 1 on the right.

## How the assembly decides true or false

The existing generator computes the right tree child, saves it with
`push %rax`, computes the left child, then restores the right value with
`pop %rdi`. For `1<2`, it emits:

```asm
  .globl main
main:
  mov $2, %rax
  push %rax
  mov $1, %rax
  pop %rdi
  cmp %rdi, %rax
  setl %al
  movzb %al, %rax
  ret
```

`.globl main` exposes the function to the linker, and `main:` marks its
entry. AT&T syntax puts the source first. Immediately before `cmp`, `%rax`
contains the left value (1) and `%rdi` the right value (2). The comparison
sets processor flags as though it computed `1-2`; it does not store that
subtraction. `setl %al` uses the signed less-than condition to put 1 in
the low byte of `%rax`. `movzb %al, %rax` then clears the remaining bytes,
so `%rax` is exactly 0 or 1. Without that step, old bits in `%rax` could
remain in the returned value.

The other cases use `sete` for equality, `setne` for inequality, and
`setle` for signed less-than-or-equal. For `>` and `>=`, the parser's
operand swap makes `setl` and `setle` sufficient. All comparisons are
signed, so `-1<0` returns 1. Addition, subtraction, multiplication,
division, and unary negation still produce values for comparisons; Python
does not evaluate those expressions itself.

## Run it in WSL

On x86-64 Linux with Python 3 and GCC (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py '5+6*7==47' > /tmp/chibicc-python-lesson7.s
cat /tmp/chibicc-python-lesson7.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson7 /tmp/chibicc-python-lesson7.s
/tmp/chibicc-python-lesson7
echo $?
```

The last command prints **1**. The executable itself prints nothing;
`echo $?` displays its exit status. Run that command immediately after the
executable. The compiler's own successful exit status is 0. GCC assembles
and links the emitted assembly with the C runtime. `-static` follows the
original tests; `-Wl,-z,noexecstack` marks the stack non-executable.

## Scope and Python/C differences

The port still accepts numeric tokens only from 0 through 2147483647.
A leading `-` is a unary operator, so `-2147483647` works but
`-2147483648` is rejected because its positive numeric token exceeds the
limit. The original stores an unchecked `strtoul` result in an `int`, with
nonportable behavior beyond that range. Our explicit check produces a
caret diagnostic. Arithmetic intermediates and comparisons use 64-bit
registers, matching the assembly generated at this stage.

Python uses lists and dataclass nodes instead of C linked lists and structs.
The `>` and `>=` tree rewrites follow C exactly. Python stores token source
positions as character indices instead of C byte offsets, accepts Unicode
whitespace, and buffers assembly until compilation succeeds. Tabs and wide
characters can still make the basic caret display appear misaligned.
Division by zero in the executable remains unchecked, as in the original.

## Tests and stopping point

```sh
python3 python/test.py
```

The tests retain all earlier valid expressions and all 26 upstream
assertions through this commit. They check two-character token boundaries,
parser precedence, the operand swap for `>` and `>=`, exact assembly for
all six operators, signed comparisons, executable exit statuses, and caret
diagnostics. Build artifacts use automatically cleaned temporary folders.

Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed. The full
notice remains in `LICENSE` here and in the repository root; this port
uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
