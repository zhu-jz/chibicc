# Lesson 61: Void and void pointers

Original chibicc commit: [`8c3503bb94bd6b2d57e1f979d9fc1d84383b2961`](https://github.com/rui314/chibicc/commit/8c3503bb94bd6b2d57e1f979d9fc1d84383b2961).
Earlier explanations are available in Git history.

## What changed

Void is a type, and `void *` declares a pointer whose pointed-to type is void.
The pointer itself still occupies eight bytes. A local variable declared
directly as void is rejected at the token after its declarator. Dereferencing
a void pointer is rejected during type annotation, including inside sizeof;
without an object type there is no value to load.

Upstream assigns void size/alignment 1 here. This is an implementation choice
that also makes void-pointer arithmetic byte-wise, a GNU extension. A void
return type and an empty function body can be declared, but `f(void)`, bare
`return;`, signature checking, and full global/return validation are not added
by this commit. Calls still receive the intermediate long type.

Python adds a Type singleton and explicit CompileError checks, matching the
valid behavior and diagnostics of this original step. Conversion between an
object pointer and void pointer uses the same address bits; no runtime Python
conversion or extra target instruction is involved.

## Assembly and WSL example

```sh
printf 'int main(){int x=42;void *p=&x;int *q=p;return *q;}\n' > /tmp/lesson61.c
python3 python/main.py -o /tmp/lesson61.s /tmp/lesson61.c
cat /tmp/lesson61.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson61 /tmp/lesson61.s
/tmp/lesson61
echo $?
```

The pointer assignments store/load eight-byte addresses. Dereferencing q,
which points to int, uses the four-byte sign-extending load. The result is 42;
the shell displays its status and the executable prints nothing. Tests cover
pointer size, passing an address through void pointers, an unused void call,
the one-byte arithmetic extension, and forbidden void locals/dereferences.
The updated upstream variable fixture and complete C fixture suite also run.

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
