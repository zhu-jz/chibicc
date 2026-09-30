# Lesson 18: license and project documentation

This educational Python port follows original chibicc commit
[`5b142b1dcf6561df3c44a743965af3bd4e619112`](https://github.com/rui314/chibicc/commit/5b142b1dcf6561df3c44a743965af3bd4e619112),
“Add LICENSE and README.md.” Earlier lessons remain in Git history.

## What changed

Upstream adds the MIT license, crediting Rui Ueyama, and a README identifying
chibicc as the reference implementation of the
[compiler book](https://www.sigbus.info/compilerbook).

This port already included the original license from the first lesson, as
requested. [LICENSE](LICENSE) contains that exact notice. This lesson records
upstream's documentation step without changing compiler behavior. It adds no
syntax or assembly instructions.

## Current compiler and assembly

The compiler still accepts a single braced program, with integer arithmetic,
variables, assignments, returns, blocks, if/else, for, and while statements.
It emits x86-64 Linux assembly defining `main`.

For example, `{ return 42; }` produces:

```asm
  .globl main
main:
  push %rbp
  mov %rsp, %rbp
  sub $0, %rsp
  mov $42, %rax
  jmp .L.return
.L.return:
  mov %rbp, %rsp
  pop %rbp
  ret
```

The prologue saves the caller's frame pointer. With no locals, no additional
stack space is required. `mov $42, %rax` sets the return value; the jump
reaches common cleanup, restores the frame, and returns to the C runtime.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository
root on x86-64 Linux:

```sh
python3 python/main.py '{ return 42; }' > /tmp/chibicc-python-lesson18.s
cat /tmp/chibicc-python-lesson18.s
gcc -static -Wl,-z,noexecstack -o /tmp/chibicc-python-lesson18 /tmp/chibicc-python-lesson18.s
/tmp/chibicc-python-lesson18
echo $?
```

The last command prints **42**. The executable prints nothing itself;
`echo $?` immediately afterward shows its exit status. Use an ordinary
interactive shell: `set -e` would stop a script on status 42.

## Verification and Python/C differences

The license was compared with the original commit's license, and the example
was checked for both its assembly and executable exit status. The existing
test suite remains available:

```sh
python3 python/test.py
```

Python uses lists and dataclasses for C linked lists and structs, and `None`
for null pointers. It accepts Unicode whitespace and reports character
positions. Decimal tokens are limited to 0 through 2147483647. These
differences are unchanged by this documentation commit.

The implementation remains in `python/` on `python-lessons`; original C
files are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT
licensed. This port preserves the full notice and uses the same license.
