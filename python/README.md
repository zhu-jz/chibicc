# Lesson 206: Treat function dereference as identity

Original chibicc commit: [`e0b5da3b395e46bbc2e377a59d5cba33206288a9`](https://github.com/rui314/chibicc/commit/e0b5da3b395e46bbc2e377a59d5cba33206288a9).
Earlier explanations are available in Git history.

Unary * now checks its operand type. A function operand is returned unchanged;
a function pointer still gets a DEREF node. After the first pointer dereference,
additional stars see a function and are harmless. This follows C's unusual
function-designator rule without emitting any extra memory loads.

```sh
printf 'int f(int x){return x+1;}int main(void){return (***f)(41);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly takes f's address and performs the usual indirect call through r10.
The stars introduce no instructions. Tests compare emitted instructions and
run direct-function and function-pointer forms, plus the upstream fixture.
Python returns the existing node and updated index where C uses an output
pointer for its remaining token. Ordinary object dereference is unchanged.

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
