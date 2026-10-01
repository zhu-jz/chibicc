# Lesson 237: Join ordinary and wide string literals

Original chibicc commit: [`238277714ddc407f966f3c503e13a114d6a91630`](https://github.com/rui314/chibicc/commit/238277714ddc407f966f3c503e13a114d6a91630).
Earlier explanations are available in Git history.

Adjacent ordinary strings now adopt a neighboring L/u/U encoding before
concatenation. The compiler re-reads each ordinary source spelling in that
encoding, so literal Unicode characters become wide units, while numeric byte
escapes retain their individual numeric values. Different non-ordinary kinds
are rejected with the original diagnostic.

The Python joining loop is generalized to remove whole element terminators
and compute an element count, matching the original's existing second pass.
It preserves token metadata while re-reading payloads, rather than overwriting
C token structs. Early -E output still prints the first source spelling only.

```sh
cat > /tmp/lesson.c <<'C'
int main(void){unsigned short x[]="α" u"β";return x[1]-904;}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Both literals become UTF-16 and one zero terminator remains. Array initialization
stores those units and x[1] is 946. Tests verify both orders, surrogate values,
wide/wide joining, initializer use, numeric escape re-reading, incompatible
prefix errors and original fixtures. The original's exact-spelling u8 kind
check does not recognize a complete u8 string token; we retain that historical
classification quirk rather than promising every mixed-prefix extension.

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
