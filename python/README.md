# Lesson 15: if and else

This educational Python port implements original chibicc commit
[`72b841508f562c65b427a502fe6b270c3717319b`](https://github.com/rui314/chibicc/commit/72b841508f562c65b427a502fe6b270c3717319b),
“Add \"if\" statement.” Earlier lessons remain in Git history; lesson 14
is Python commit `59ade10`.

## What changed

A program can now choose which statement to execute:

```c
{ if (0) return 2; return 3; }
{ if (1) return 2; else return 3; }
```

The first returns 3; the second returns 2. Zero means false and any nonzero
value means true, including negative values and 256. The full 64-bit value
is tested, not just its low byte.

A branch can be a return, an expression statement, a block, a null statement,
or another if statement. For example:

```c
{ a=0; if (1) { a=3; a=a+2; } else a=8; return a; }
```

This returns 5. Only the selected branch executes, but the compiler parses
and generates both branches. Even an unselected branch must be valid code.

## Parser and tree

The tokenizer now recognizes the complete words `if` and `else` as keywords,
along with `return`. Longer names such as `ifx` and `elsewhere` remain
identifiers. The new statement rule is:

```text
stmt = "if" "(" expr ")" stmt ("else" stmt)?
```

Parentheses around the condition are required. The `?` means the else
part is optional. `Parser.stmt()` builds an `IF` node with three fields:
`cond` for the condition, `then` for the true branch, and `els` for the
optional false branch.

The true branch is parsed by recursively calling `stmt()`. As a result,
an `else` belongs to the nearest unmatched `if`:

```c
{ if (1) if (0) return 2; else return 3; return 4; }
```

Here the else belongs to `if (0)`, and the program returns 3. To associate
an else with an outer if, place the inner if inside braces. `else if` needs
no special grammar: it is an else branch containing another if statement.

## Read the assembly

For `{ if(1) 2; else 3; }`, the body instructions are:

```asm
  mov $1, %rax
  cmp $0, %rax
  je  .L.else.1
  mov $2, %rax
  jmp .L.end.1
.L.else.1:
  mov $3, %rax
.L.end.1:
```

The condition is evaluated into `%rax`. `cmp $0, %rax` sets processor flags
according to whether that value is zero. `je` jumps to the else label when
it is zero. Otherwise execution falls through into the true branch.
The unconditional `jmp` skips the false branch after the true branch
finishes. Both paths meet at the end label.

Each if statement gets its own number, so nested or consecutive statements
do not reuse labels. The generator saves the number in a local Python
variable before recursively generating branches. Without an else branch,
it still emits both labels, with no code between them, matching upstream.
Return statements inside either branch still jump to `.L.return` for
function cleanup.

## Run it in WSL

With Python 3 and GCC on x86-64 Linux (`python3` and `build-essential` on
Ubuntu), run from the repository root:

```sh
python3 python/main.py '{ if (0) return 2; else return 3; }' > /tmp/chibicc-python-lesson15.s
cat /tmp/chibicc-python-lesson15.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson15 /tmp/chibicc-python-lesson15.s
/tmp/chibicc-python-lesson15
echo $?
```

The last command prints **3**. The executable prints nothing; `echo $?`
immediately afterward displays its exit status. Quote the source so the
shell passes its braces, semicolons, and operators literally. Use an
ordinary interactive shell: `set -e` would stop a script on status 3.

The function still establishes a stack frame, reserves aligned local
storage, and restores it at `.L.return` before `ret`. GCC assembles and
links our emitted code with the C runtime. `-static` follows upstream tests;
`-Wl,-z,noexecstack` marks the stack non-executable. Python does not use
`eval()` or invoke the original C compiler.

## Python/C differences and tests

The original C generator uses a static counter starting at 1. This port
keeps the counter on each `CodeGenerator` instance, producing the same label
numbers for a compilation while keeping separate compilations independent.
The `IF` node fields and emitted branches follow upstream. Python lists
and dataclasses continue to replace C linked lists and structs.

Existing limits remain: numeric tokens range from 0 through 2147483647,
variables are uninitialized before assignment, deep nesting may reach
Python's recursion limit, and runtime division by zero is unchecked.
Normal exit statuses retain eight bits even though conditions test the
full register. Python accepts Unicode whitespace and uses character-based
diagnostic positions. Assembly is printed only after successful compilation.
The original parser's unchecked trailing tokens after the outer block are
still preserved in this lesson.

```sh
python3 python/test.py
```

Tests include all six new upstream examples and retain the previous
executable cases. They check false and nonzero conditions, assignments in
conditions, branch side effects, nested and consecutive if statements,
nearest-if binding of else, empty branches, distinct labels, exact assembly,
keyword boundaries, and invalid syntax. Temporary artifacts are cleaned up.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in `LICENSE` here and in the repository
root; this port uses the same license.

Stop here until you explicitly confirm understanding and readiness for the
next original commit.
