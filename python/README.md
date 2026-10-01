# Lesson 259: Emit basic inline assembly statements

Original chibicc commit: [`a2535163e232cd547b14960bf4232305d239741d`](https://github.com/rui314/chibicc/commit/a2535163e232cd547b14960bf4232305d239741d).
Earlier explanations are available in Git history.

The parser now accepts `asm`, optional inline/volatile modifiers and a narrow
string literal in parentheses. An ASM node stores the decoded string, and the
statement generator writes it directly into the emitted assembly. Adjacent
literals have already been joined by preprocessing.

```sh
printf '%s\n' 'int f(void){asm("mov $42, %rax\nmov %rbp, %rsp\npop %rbp\nret");}int main(void){return f();}' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The supplied instructions set rax to 42, restore the frame and return directly
from f. Main calls f and returns that value. Restoring the frame is necessary
because the compiler emitted f's prologue before the asm statement. Tests inspect
the literal assembly, run modifier and concatenation cases, reject wide strings,
and execute the original asm.c functions.
This is basic asm only: there are no operand constraints or clobber lists. Python
stores decoded text instead of C's byte pointer; embedded NUL truncates the text
as in C, and invalid UTF-8 bytes become replacement characters. The original
parser leaves a following semicolon for the next empty statement to consume.

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
