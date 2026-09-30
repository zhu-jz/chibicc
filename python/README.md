# Lesson 16: for loops

This educational Python port implements original chibicc commit
[`f5d480f139592cc2670c2b05076c39b2fd6fe9b3`](https://github.com/rui314/chibicc/commit/f5d480f139592cc2670c2b05076c39b2fd6fe9b3),
“Add \"for\" statement.” Earlier lessons remain in Git history.

## What changed

A program can now repeat a statement:

```c
{ i=0; sum=0; for(i=0; i<=10; i=i+1) sum=sum+i; return sum; }
```

This returns 55. The initialization runs once. Before each iteration, the
condition is evaluated: zero ends the loop, and any nonzero value runs the
body. The increment runs after the body, then execution checks the condition
again. A return inside the body jumps directly to the function epilogue.

Each part of the header is optional. The semicolons are still required.
An absent condition means the loop continues indefinitely unless its body
returns. For example, `{ for (;;) return 3; }` returns 3. A body can be a
block, another control statement, an expression statement, or a lone `;`.

## Parser and tree

The tokenizer recognizes the complete word `for` as a keyword. Names such
as `format` remain identifiers. The new grammar is:

```text
stmt = "for" "(" expr-stmt expr? ";" expr? ")" stmt
```

An expression statement includes its terminating semicolon, so parsing the
initialization consumes the first separator. A new `FOR` node stores
`init`, `cond`, `inc`, and `then` (the body). A missing initialization is an
empty `BLOCK`, matching the existing representation of a null statement.
Missing condition and increment fields are `None`.

## Read the assembly

The loop body for `{ for (;;) return 3; }` is:

```asm
.L.begin.1:
  mov $3, %rax
  jmp .L.return
  jmp .L.begin.1
.L.end.1:
```

The begin label marks the next condition check. When a condition exists,
the compiler evaluates it into `%rax`, emits `cmp $0, %rax`, and uses
`je .L.end.1` to leave the loop if it is zero. The body and increment follow,
then `jmp .L.begin.1` repeats. Here there is no condition or increment, and
the return jumps out before the backward jump can execute.

Loops and if statements share a label counter so nested control flow has
distinct labels. The function still saves `%rbp`, reserves stack space for
locals, and restores its frame at `.L.return` before `ret`.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{ i=0; sum=0; for(i=0; i<=10; i=i+1) sum=sum+i; return sum; }' > /tmp/chibicc-python-lesson16.s
cat /tmp/chibicc-python-lesson16.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson16 /tmp/chibicc-python-lesson16.s
/tmp/chibicc-python-lesson16
echo $?
```

The last command prints **55**. The executable prints nothing itself;
`echo $?` immediately afterward displays its exit status. Quote the source
to pass it as one shell argument. Use an ordinary interactive shell:
`set -e` would stop a script on status 55.

GCC assembles and links the emitted assembly with the C runtime. `-static`
follows upstream tests; `-Wl,-z,noexecstack` marks the stack non-executable.
Python parses the source and emits instructions; it does not evaluate the
program or wrap the original C compiler.

## Python/C differences and tests

Python `None` replaces C null pointers for optional fields. Lists and
dataclasses replace linked lists and structs. The generator's label counter
belongs to each compilation rather than being a C static variable.

Existing limits remain: numeric tokens range from 0 through 2147483647,
locals are uninitialized before assignment, runtime division by zero is
unchecked, and deep syntax may reach Python's recursion limit. Python accepts
Unicode whitespace and reports positions in characters. The outer parser
still ignores tokens after the closing program brace, matching this stage
of upstream. Exit statuses keep only eight bits of the returned value.

```sh
python3 python/test.py
```

Tests retain earlier examples and cover the new upstream examples, omitted
header clauses, zero iterations, nested loops, an empty body, keyword
boundaries, invalid headers, tree fields, and generated assembly. New loop
execution checks use a timeout and clean up temporary files.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
