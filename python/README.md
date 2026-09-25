# Lesson 12: return statements

This educational Python port implements original chibicc commit
[`6cc1c1f0643ce0f1af0857e024a0a438ddb45853`](https://github.com/rui314/chibicc/commit/6cc1c1f0643ce0f1af0857e024a0a438ddb45853),
“Add \"return\" statement.” Earlier lessons remain in Git history;
lesson 11 is Python commit `7760b36`.

## What changed

You can explicitly finish the function and select its result:

```text
return 1; 2; 3;    → 1
1; return 2; 3;    → 2
1; 2; return 3;    → 3
```

The returned expression is evaluated before leaving the function. For
`foo=7; return (foo+5)*(foo-2); foo=99;`, the result is 60 and the last
assignment never executes.

The statement grammar gains one alternative:

```text
stmt = "return" expr ";" | expr-stmt
```

An expression and terminating semicolon are required. `return;` and
`return 1` are errors. All existing expression operators and variables
can be used inside the returned expression.

## Keyword, tree node, and jump

After scanning tokens, `tokenizer.py` converts the exact word `return`
from an identifier to a `KEYWORD`. Complete names are recognized before
this conversion, so `returnx`, `return_`, and `Return` are still ordinary
variable names. `return` itself can no longer be a variable.

`Parser.stmt()` in `parse.py` recognizes that keyword, parses its expression,
requires `;`, and constructs `Node("RETURN", lhs=expression)`. The program
still stores statements in source order, including those after a return.

`CodeGenerator.gen_stmt()` emits the expression into `%rax`, followed by:

```asm
  jmp .L.return
```

The shared `.L.return` label is placed immediately before the existing
function epilogue. That epilogue frees local-variable storage, restores
the caller's `%rbp`, and returns. Jumping there ensures every return uses
the same cleanup code. A direct `ret` at the statement would encounter
the function's current stack frame instead of the caller's return address.

## Read the assembly

For `return 3; 42;`, the exact output is:

```asm
  .globl main
main:
  push %rbp
  mov %rsp, %rbp
  sub $0, %rsp
  mov $3, %rax
  jmp .L.return
  mov $42, %rax
.L.return:
  mov %rbp, %rsp
  pop %rbp
  ret
```

`.globl main` exposes the entry point to the linker. The prologue saves
`%rbp` and establishes the stack frame; this example uses zero local bytes.
`mov $3, %rax` sets the result. `jmp` transfers execution directly to the
label, skipping `mov $42, %rax`. The epilogue preserves `%rax`, so the
runtime receives 3.

The compiler still generates the skipped instruction. This commit does
not remove unreachable code. It also parses and checks all later statements:
`return 1; 1=3;` remains a compilation error because 1 is not assignable.

## Run it in WSL

With Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py 'return 3; 42;' > /tmp/chibicc-python-lesson12.s
cat /tmp/chibicc-python-lesson12.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson12 /tmp/chibicc-python-lesson12.s
/tmp/chibicc-python-lesson12
echo $?
```

The last command prints **3**. The executable prints nothing itself;
`echo $?` immediately afterward displays its exit status. Quote the input
so the shell does not interpret its semicolons. Use an ordinary interactive
shell: `set -e` would stop a script on status 3. The compiler's own successful
status is 0.

GCC assembles and links our output with the C runtime. `-static` follows
the original tests and `-Wl,-z,noexecstack` marks the stack non-executable.
The Python compiler neither evaluates the source using `eval()` nor invokes
the original C compiler.

## Existing behavior and Python/C differences

Programs without an explicit return remain accepted. Reaching the end
still returns the final expression's value at this stage. Empty programs
leave the result unspecified. Variables remain uninitialized until assigned.
A normal Linux exit status retains eight bits, so `return -7;` gives 249.

The new keyword conversion, return node, jump, and label follow the original
commit. Python continues to use dataclasses, statement lists, a parser
instance with its own locals, and assembly buffered until compilation
succeeds. Numeric tokens have an explicit range of 0 through 2147483647;
the original's unchecked conversion differs outside that range. Python
accepts Unicode whitespace and counts character positions for diagnostics,
while identifier characters remain ASCII. Deep expression trees can reach
Python's recursion limit; runtime division by zero remains unchecked.

## Tests and attribution

```sh
python3 python/test.py
```

Tests include the upstream return examples and retain all prior executable
cases. They check keyword boundaries, return tree structure, exact jump and
label assembly, early exit before later statements, multiple returns,
returns using locals and assignment, and missing-expression/semicolon
errors. Invalid code after a return must still be rejected. Temporary
assembly and executable artifacts are cleaned up automatically.

All implementation files remain in `python/` on `python-lessons`, with the
original C files intact. Original chibicc: Copyright (c) 2019 Rui Ueyama,
MIT licensed. The complete notice remains in `LICENSE` here and at the
repository root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
