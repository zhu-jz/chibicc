# Lesson 107: Global union initializers and relocations

Original chibicc commit: [`1eae5ae3678d079efc7d2807f10439e53932f811`](https://github.com/rui314/chibicc/commit/1eae5ae3678d079efc7d2807f10439e53932f811).
Earlier explanations are available in Git history.

## What changed

Global union serialization writes the first member at offset zero. This original
commit also adds address initializers. The evaluator now returns an integer
addend plus an optional symbol, letting `g+1`, `&g.member`, string addresses,
and nested array-member addresses become relocations. Arithmetic scales pointer
steps to bytes before constant evaluation.

Relocation records contain an offset within the initialized object, a symbol
name, and an addend. The data emitter writes .quad at each relocation and .byte
elsewhere. The assembler/linker resolves final addresses. Numeric-only constant
contexts still reject addresses; ordinary global scalar reads cannot initialize
another global. This step's address relocations assume eight-byte storage.

Python tuples replace C's label output pointer, and lists replace linked
relocation records. Byte serialization explicitly targets little-endian x86-64.
The constant evaluator still preserves earlier historical cast behavior.

## Assembly and WSL example

```sh
printf 'int g[2]={1,42};int *p=g+1;int main(){return *p;}\n' > /tmp/lesson107.c
python3 python/main.py /tmp/lesson107.c > /tmp/lesson107.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson107 /tmp/lesson107.s
/tmp/lesson107
echo $?
```

The data for p is `.quad g+4`, because each int occupies four bytes. Main loads
p then dereferences it, returning 42. Tests cover signed addends, pointer arrays,
member offsets, strings, conditional addresses, union data, relocation records,
assembly, invalid scalar reads, and the expanded original C initializer suite.

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
