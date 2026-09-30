# Lesson 77: Compound assignments

Original chibicc commit: [`01a94c04aa2b5a95ac4038bd0d6fd5334fcbf882`](https://github.com/rui314/chibicc/commit/01a94c04aa2b5a95ac4038bd0d6fd5334fcbf882).
Earlier explanations are available in Git history.

## What changed

The tokenizer recognizes +=, -=, *=, and /=. The parser lowers `A op= B` to
`tmp=&A, *tmp=*tmp op B`, where tmp is a fresh anonymous local pointer. Saving
the address ensures a side effect in A occurs only once. The resulting expression
returns the assigned value. Pointer +=/-= reuse element-size scaling, and normal
assignment conversion handles narrow destination types. No new code-generation
node is required: comma, address, dereference, arithmetic, and assignment suffice.

Python constructs separate VAR nodes referring to the same temporary Obj; C
builds equivalent nodes with pointers. The anonymous slot participates in normal
stack allocation. Evaluation order follows this lowering and the existing emitter.

## Assembly and WSL example

```sh
printf 'int main(){int x=2;x+=5;return x;}\n' > /tmp/lesson77.c
python3 python/main.py /tmp/lesson77.c > /tmp/lesson77.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson77 /tmp/lesson77.s
/tmp/lesson77
echo $?
```

`lea` computes x's address, a 64-bit store saves it in tmp, and the second
assignment loads/adds/stores x through that pointer. The program exits with 7.
Tests cover returned values, all four operators, nested assignments, pointer
scaling, narrow conversions, one address evaluation, invalid lvalues, and the
updated original arithmetic programs.

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
