# Lesson 118: Alignment queries and overrides

Original chibicc commit: [`9df51789e7fd36fc1580bcd80676f9bcc4e24be1`](https://github.com/rui314/chibicc/commit/9df51789e7fd36fc1580bcd80676f9bcc4e24be1).
Earlier explanations are available in Git history.

## What changed

_Alignof(type) becomes a constant number describing type alignment. _Alignas(type)
or _Alignas(constant) overrides alignment for declared variables and members.
Objects and members now store alignment separately from their Type, so aligning
one int to 32 does not change _Alignof(int), which remains 4. Stack offsets,
global directives, and struct/union layout use these separate alignments.

Python stores the new values on dataclasses and parses the two argument forms
with existing type-name and constant-expression routines. As upstream, this step
does not fully validate requested alignments or realign the stack base for large
local alignment; tests check local spacing rather than a stronger guarantee.
For-loop and parameter contexts still reject _Alignas. The member parser now
accepts storage attributes like upstream, without applying complete validation.

## Assembly and WSL example

```sh
printf 'int main(){_Alignas(32) char x,y;return &y-&x;}\n' > /tmp/lesson118.c
python3 python/main.py /tmp/lesson118.c > /tmp/lesson118.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson118 /tmp/lesson118.s
/tmp/lesson118
echo $?
```

Stack offsets are rounded separately to multiples of 32, putting these chars
32 bytes apart. Address subtraction returns exit status 32. Tests cover type
queries, type/numeric overrides, separate object and type alignment, struct
member gaps, union alignment, emitted global directives, rejected contexts,
real execution, and the new original alignof program.

## Tests and attribution

Run from the repository root on x86-64 Linux/WSL with Python 3 and GCC
(`build-essential` on Ubuntu):

```sh
python3 python/test.py
```

The tests check emitted assembly and assemble/link/run real executables;
temporary artifacts are cleaned up and execution has a timeout.
Python builds syntax trees and emits assembly; it does not use `eval()`
or invoke the original compiler. Python lists, dataclasses, tuples, and
`None` replace C linked lists, structs, output pointers, and null pointers.
Unicode whitespace and character-based diagnostic positions are intentional
Python differences. Any further differences for this step are described above.

The implementation is in `python/` on `python-lessons`. Original C files
are intact. Original chibicc: Copyright (c) 2019 Rui Ueyama, MIT licensed.
The full notice is preserved in [LICENSE](LICENSE); this port uses the same license.
