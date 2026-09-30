# Lesson 17: while loops

This educational Python port implements original chibicc commit
[`1f3eb34f637520b01e6b8cd10a9026d05036db6d`](https://github.com/rui314/chibicc/commit/1f3eb34f637520b01e6b8cd10a9026d05036db6d),
“Add \"while\" statement.” Earlier lessons remain in Git history.

## What changed

A program can now repeat a statement while a condition is true:

```c
{ i=0; while(i<10) i=i+1; return i; }
```

This returns 10. The condition is checked before every iteration. Zero
ends the loop; any nonzero value, including a negative value, runs the body.
A false initial condition skips the body entirely. The body can be a block,
a return, an expression statement, an empty statement, or another loop.

## Parser and tree

The tokenizer recognizes the complete word `while` as a keyword. Names
such as `whilex` remain identifiers. The new statement rule is:

```text
stmt = "while" "(" expr ")" stmt
```

The condition and parentheses are required. The parser reuses the `FOR`
node introduced in lesson 16, setting `cond` and `then` (the body), and
leaving `init` and `inc` as `None`. Thus `while(x)` and `for(;x;)`
generate the same assembly.

Code generation now checks whether `init` exists before generating it.
A for loop's empty initialization is an empty `BLOCK`; a while loop has
no initialization node at all. Both correctly emit no initialization code.

## Read the assembly

For `{ while(1) return 3; }`, the loop body is:

```asm
.L.begin.1:
  mov $1, %rax
  cmp $0, %rax
  je  .L.end.1
  mov $3, %rax
  jmp .L.return
  jmp .L.begin.1
.L.end.1:
```

The begin label marks the condition check. The condition's value goes into
`%rax`; `cmp` and `je` leave the loop if it is zero. Otherwise the body
executes, and the backward `jmp` repeats. Here the return jumps directly
to the function epilogue, so the backward jump is never reached.

A variable condition is reevaluated on every pass, so changes made by the
body affect the next check. Loops and if statements share a counter that
gives each control statement distinct labels. The existing stack frame and
`.L.return` cleanup remain unchanged.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{ i=0; while(i<10) i=i+1; return i; }' > /tmp/chibicc-python-lesson17.s
cat /tmp/chibicc-python-lesson17.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson17 /tmp/chibicc-python-lesson17.s
/tmp/chibicc-python-lesson17
echo $?
```

The last command prints **10**. The executable prints nothing itself;
`echo $?` immediately afterward displays its exit status. Quote the source
to pass it as one shell argument. Use an ordinary interactive shell:
`set -e` would stop a script on status 10.

GCC assembles and links the emitted assembly with the C runtime. `-static`
follows upstream tests; `-Wl,-z,noexecstack` marks the stack non-executable.
Python parses the source and emits instructions; it does not evaluate the
loop or wrap the original C compiler.

## Python/C differences and tests

Python `None` replaces C null pointers for absent initialization and
increment fields. Lists and dataclasses continue to replace linked lists
and structs. The compiler creates a fresh label counter per compilation.

Existing limits remain: numeric tokens range from 0 through 2147483647,
locals are uninitialized before assignment, runtime division by zero is
unchecked, and deep syntax may reach Python's recursion limit. Python accepts
Unicode whitespace and reports positions in characters. The outer parser
still ignores tokens after the closing program brace, matching this stage
of upstream. Exit statuses keep only eight bits of the returned value.

```sh
python3 python/test.py
```

Tests retain earlier examples and cover the new upstream loop, zero
iterations, negative conditions, variable updates, nested for/while loops,
keyword boundaries, a missing condition, the reused tree fields, and
identical assembly for equivalent for and while loops. New loop execution
checks use a timeout and clean up temporary files.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. The full notice remains in [LICENSE](LICENSE), and this port uses
the same license.
