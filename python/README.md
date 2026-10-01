# Lesson 148: Floating constant expressions

Original chibicc commit: [`ffea4219b1f4ebe7c06cecc6c221cb0aab3a03ea`](https://github.com/rui314/chibicc/commit/ffea4219b1f4ebe7c06cecc6c221cb0aab3a03ea).
Earlier explanations are available in Git history.

## What changed

Global float and double initializers now evaluate arithmetic, negation, casts,
conditionals, and comma expressions. A dedicated syntax-tree walker computes in
double precision; global float storage rounds to four bytes, and double storage
uses eight bytes. Integer constant evaluation truncates floating results when it
needs an integer. Runtime calculations continue to use generated SSE instructions.

Python's struct module writes explicitly little-endian IEEE bytes instead of C
pointer casts into a character buffer. Floating division by zero is handled
explicitly to produce infinity or NaN, matching the ordinary target environment.
A non-finite result converted to an integer gets a clear error instead of relying
on undefined C conversion behavior. The historical evaluator does not round every
intermediate float cast and retains its signed integer-to-floating cast rules.

## Assembly and WSL example

```sh
printf 'float g=21.5*2-1;int main(void){return g;}\n' > /tmp/lesson148.c
python3 python/main.py /tmp/lesson148.c > /tmp/lesson148.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson148 /tmp/lesson148.s
/tmp/lesson148
echo $?
```

The .data bytes 0,0,40,66 encode float 42.0. Main loads them with movss and
converts xmm0 to integer 42. The shell displays that exit status. Tests cover
exact bytes, aggregates, casts, conditionals, infinity/NaN, unsupported calls,
assembly, real execution, and the original constant-expression fixture.

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
