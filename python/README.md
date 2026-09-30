# Lesson 79: Postfix increment and decrement

Original chibicc commit: [`e8ca48cf41f5f3113cadfb23acfedad7b9fa2e63`](https://github.com/rui314/chibicc/commit/e8ca48cf41f5f3113cadfb23acfedad7b9fa2e63).
Earlier explanations are available in Git history.

## What changed

Postfix x++ updates x but returns its previous value. This commit lowers it to
`(type of x)((x += 1) - 1)`; x-- uses an addend of -1 and reverses that afterward.
The compound-assignment helper evaluates the address once. Pointer scaling works
for both the update and reverse adjustment. The final cast restores char/short
width, including boundary wrapping. Postfix binds tightly: *p++ dereferences the
old pointer and advances p, whereas (*p)++ updates the pointed-to object.

Python uses the same lowering, not a special runtime evaluator. This historical
update-then-reverse strategy is imperfect for _Bool at value 1; general postfix
semantics are not fully mature yet. Signed overflow remains outside portable C.

## Assembly and WSL example

```sh
printf 'int main(){int x=42;return x++;}\n' > /tmp/lesson79.c
python3 python/main.py /tmp/lesson79.c > /tmp/lesson79.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson79 /tmp/lesson79.s
/tmp/lesson79
echo $?
```

The emitter stores 43 into x, then adds -1 to the expression result, returning
42. Tests cover old/updated values, pointer precedence, side-effecting targets,
char boundary conversion, sizeof suppression, tree types, invalid lvalues, and
the original arithmetic/sizeof tests.

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
