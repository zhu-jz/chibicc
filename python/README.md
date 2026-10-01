# Lesson 244: Find fields inside anonymous structs

Original chibicc commit: [`95eb5b01b30b24d68cbeb3991f65c617fc2a35cb`](https://github.com/rui314/chibicc/commit/95eb5b01b30b24d68cbeb3991f65c617fc2a35cb).
Earlier explanations are available in Git history.

A struct designator can now name a field inside an anonymous struct member.
The lookup first selects the anonymous container, then leaves `.field` unconsumed
so recursive designation can find the inner field. Ordinary named members still
advance past the field name immediately.

```sh
printf 'int main(void){struct{struct{int a,b;};int c;}x={.b=12,30};return x.a+x.b+x.c;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly zeroes the object, stores 12 into the inner b field and 30 into c,
then loads and adds them. The anonymous struct contributes its member offsets
but needs no extra runtime representation. Tests cover nested anonymous structs,
global initialization and an anonymous struct inside a union, plus original fixtures.
Python returns a Member and token-list index instead of a C pointer and output
parameter. This original step searches anonymous structs; anonymous union lookup
in initializer designators is not extended here.

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
