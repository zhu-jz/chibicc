# Lesson 53: Member access through pointers

Original chibicc commit: [`f0a018a7d6f5e3847d7e66e324c5f71a55c8b5ef`](https://github.com/rui314/chibicc/commit/f0a018a7d6f5e3847d7e66e324c5f71a55c8b5ef).
Earlier explanations are available in Git history.

## What changed

The tokenizer recognizes `->` as one punctuation token. Postfix parsing rewrites
`p->field` into a DEREF node for p followed by the existing MEMBER node. This
is exactly the operation described by `(*p).field`: obtain the pointed-to
struct, then select its field. Chains such as `p->next->value` and combinations
with array subscripts work through the same postfix loop.

No code-generation rule is added. Address generation for DEREF evaluates the
pointer expression; MEMBER then adds the field offset. Reading the selected
member loads its type, while assigning to it stores through that address.
Type checking rejects a non-pointer dereference or a member access on an int.
As before, runtime pointer validity is not checked.

Python's ordinary nested nodes express the same lowering as upstream's C
nodes. This step introduces no additional Python/C semantic difference.

## Assembly and WSL example

```sh
printf 'int main(){struct t{int a;} x;struct t *p=&x;p->a=42;return x.a;}\n' > /tmp/lesson53.c
python3 python/main.py -o /tmp/lesson53.s /tmp/lesson53.c
cat /tmp/lesson53.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson53 /tmp/lesson53.s
/tmp/lesson53
echo $?
```

Codegen loads p's address value, adds a's offset (zero here), and stores 42
through it. The final field load returns 42 in `%rax`, so the shell displays
42. Tests execute upstream's read/write examples, array/pointer combinations,
a chain through a pointer field, and invalid types. An instruction comparison
confirms that `p->a` emits the same code as `(*p).a`; the C struct fixture is
updated and run with all other upstream C fixtures.

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
