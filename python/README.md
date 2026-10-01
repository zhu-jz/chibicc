# Lesson 124: Do-while loops

Original chibicc commit: [`ee252e6ce79d752526504cf034fd41f070191824`](https://github.com/rui314/chibicc/commit/ee252e6ce79d752526504cf034fd41f070191824).
Earlier explanations are available in Git history.

## What changed

`do statement while(condition);` becomes a DO node. The parser creates loop
break/continue labels, parses the body with those active, then restores enclosing
loop labels before parsing the condition. Code generation emits the body first,
the continue label and condition second, and a backward jump if nonzero.

Python saves the enclosing labels in local variables, matching upstream's C
locals. Unlike a while loop, this loop always executes its body once. Continue
checks the condition; break skips it. Existing nested loop and switch handling
uses the same label infrastructure.

## Assembly and WSL example

```sh
printf 'int main(){int x=40;do{++x;}while(x<42);return x;}\n' > /tmp/lesson124.c
python3 python/main.py /tmp/lesson124.c > /tmp/lesson124.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson124 /tmp/lesson124.s
/tmp/lesson124
echo $?
```

After each increment the condition compares x with 42. A `jne .L.begin...` jumps
back while the comparison result is nonzero. Main exits with 42. Tests cover an
initially false condition, repeated iterations, continue, break, nested loops,
emitted backward branch, required semicolon, execution, and upstream control code.

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
