# Lesson 83: Remainder and remainder assignment

Original chibicc commit: [`daa739817c58baa8dcd0c23bb403d27d5907abfb`](https://github.com/rui314/chibicc/commit/daa739817c58baa8dcd0c23bb403d27d5907abfb).
Earlier explanations are available in Git history.

## What changed

% joins multiplication/division precedence and undergoes usual arithmetic
conversion. %= reuses compound-assignment lowering. Signed idiv supplies both a
quotient in eax/rax and a remainder in edx/rdx; % moves the remainder into rax.
The emitter chooses cdq/idiv edi for int and cqo/idiv rdi for long.

C division truncates toward zero, so -17%6 is -5. Python's % on ints would give 1,
but the compiler never uses it to compute runtime expressions: emitted idiv
preserves the target behavior. Division by zero and signed division overflow
retain machine exceptions at this stage.

## Assembly and WSL example

```sh
printf 'int main(){int x=17;return x%%6;}\n' > /tmp/lesson83.c
python3 python/main.py /tmp/lesson83.c > /tmp/lesson83.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson83 /tmp/lesson83.s
/tmp/lesson83
echo $?
```

`idiv %edi` leaves 5 in edx, and `mov %rdx, %rax` selects that result instead of
the quotient. The shell displays 5. Tests cover operand signs, widths, %=
results, side-effecting destinations, instruction sequences, actual execution,
and all updated original programs.

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
