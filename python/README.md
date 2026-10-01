# Lesson 151: Function pointers and indirect calls

Original chibicc commit: [`d06a8ac6e6120861c9c79acb15b9a18693e4ee47`](https://github.com/rui314/chibicc/commit/d06a8ac6e6120861c9c79acb15b9a18693e4ee47).
Earlier explanations are available in Git history.

## What changed

A call is now a postfix operation on any function or function-pointer expression.
Its tree stores the callee in lhs rather than storing a function-name string.
This supports parenthesized function names, address expressions, pointer variables,
struct members, and functions returning function pointers. Argument conversions
and register classification still follow the callee's function type.

After saving arguments, the compiler evaluates the callee address and restores
argument registers, then emits call *%rax. Evaluating a function yields its
address rather than loading bytes from its code. Defined functions use RIP-relative
lea; declarations use mov name@GOTPCREL(%rip), letting the linker resolve external
function addresses. Python uses the same assembly and explicit tree nodes.

## Assembly and WSL example

```sh
printf 'int add(int x){return x+1;}int main(void){int(*p)(int)=add;return p(41);}\n' > /tmp/lesson151.c
python3 python/main.py /tmp/lesson151.c > /tmp/lesson151.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson151 /tmp/lesson151.s
/tmp/lesson151
echo $?
```

lea obtains add's address, an assignment stores it in p, and a later load puts
that address in rax. The argument 41 goes in edi and call *%rax transfers control
to add. It returns 42; the shell displays that exit status. Tests cover local and
global pointers, struct members, external functions, address instructions,
relocations, call alignment, execution, and the original function-pointer examples.

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
