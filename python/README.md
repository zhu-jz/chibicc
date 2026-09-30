# Lesson 48: Comma expressions and generalized lvalues

Original chibicc commit: [`e6307ad374eeecd6474286b1b6fda5b3dda89d9a`](https://github.com/rui314/chibicc/commit/e6307ad374eeecd6474286b1b6fda5b3dda89d9a).
Earlier explanations are available in Git history.

## What changed

`expr` now accepts a comma after an assignment expression. It recursively
parses the remainder into a COMMA node. A comma expression evaluates its left
operand for side effects, then its right operand; its value and type come from
the right. This follows upstream's right-recursive grammar. Function arguments
and declaration initializers still parse `assign`, so separator commas stay
separators unless parentheses explicitly create a comma expression.

The address generator also handles COMMA: evaluate the left operand, then
compute the right operand's address. Thus `(i=5,j)=6` sets i to 5 and j to 6.
This generalized-lvalue behavior is a deprecated GNU extension intentionally
preserved from this commit, rather than standard C behavior. A numeric right
operand still cannot be an lvalue. The Python tree stores two ordinary child
references instead of C pointers.

## Assembly and WSL example

```sh
printf 'int main(){int i=2,j=3; (i=5,j)=6; return i+j;}\n' > /tmp/lesson48.c
python3 python/main.py -o /tmp/lesson48.s /tmp/lesson48.c
cat /tmp/lesson48.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson48 /tmp/lesson48.s
/tmp/lesson48
echo $?
```

The comma needs no special machine instruction. Codegen emits the store of 5
to i, then j's address and the store of 6. The return expression loads both
variables and adds them in `%rax`; the shell displays status 11. `.file` and
`.loc` still describe source positions and do not execute.

Tests include all three upstream examples, left-to-right side effects,
parenthesized call arguments, pointer results, sizeof's right-operand type,
and rejecting a numeric lvalue. The C control fixture is updated to this
original commit; the entire upstream C fixture suite is also run.

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
