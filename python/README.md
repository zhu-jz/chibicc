# Lesson 67: Explicit type casts

Original chibicc commit: [`cfc4fa94c1eb17f37466571f74bbdfae03a6e11f`](https://github.com/rui314/chibicc/commit/cfc4fa94c1eb17f37466571f74bbdfae03a6e11f).
Earlier explanations are available in Git history.

## What changed

Cast expressions use `(` type-name `)` followed by another cast or unary
expression. Scope-aware type-name recognition distinguishes `(T)x` from a
parenthesized variable. Multiplication and unary operators now call this cast
parser, preserving precedence. A CAST node records its already-annotated
operand and a copied destination type; explicit casts keep the opening
parenthesis as their source token.

Codegen evaluates the operand and follows upstream's conversion table.
Narrowing to char/short uses `movsbl %al, %eax` or `movswl %ax, %eax`.
Widening small integers to long uses `movsxd %eax, %rax`. Casts between
pointer/long representations emit no conversion instruction. A void cast
still evaluates side effects, then performs no conversion.

The table has intermediate no-op cases, including long-to-int. A following
thirty-two-bit use observes the low bits; not every wider context has the
implicit conversion it needs yet. Full cast legality and automatic arithmetic,
assignment and call conversions are not added by this original commit.
Python emits the same table instead of evaluating casts at compile time.

## Assembly and WSL example

```sh
printf 'int main(){return (long)(short)65535<0;}\n' > /tmp/lesson67.c
python3 python/main.py -o /tmp/lesson67.s /tmp/lesson67.c
cat /tmp/lesson67.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson67 /tmp/lesson67.s
/tmp/lesson67
echo $?
```

`movswl %ax, %eax` selects and sign-extends the low word (-1), and
`movsxd %eax, %rax` extends it to long. A signed comparison produces 1,
which the shell displays as the exit status. Tests cover upstream's narrowing,
address/integer and pointer casts, nested sign extensions, typedef ambiguity,
void side effects, sizeof casts and malformed syntax. Casting a negative int
index to long also verifies a real backwards pointer access. The new cast
fixture runs with all upstream C fixtures.

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
