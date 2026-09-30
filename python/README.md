# Lesson 50: Struct member alignment

Original chibicc commit: [`9443e4b8bc587b670f9b448b03842530cd355760`](https://github.com/rui314/chibicc/commit/9443e4b8bc587b670f9b448b03842530cd355760).
Earlier explanations are available in Git history.

## What changed

Types now carry alignment as well as size. Char has size/alignment 1; int and
pointers still have size/alignment 8. An array inherits its element alignment.
Before placing each struct member, round its offset up to that member's
alignment. The struct alignment is the maximum of its members, at least 1.
Finally round the total size up to that alignment, including tail padding.

`struct {char a; int b;}` now has offsets 0 and 8, size 16 and alignment 8.
Reversing the fields still gives size 16 because tail padding follows the
char. Adding a final char gives offsets 0, 8, 16 and total size 24. Empty
structs remain size 0 with alignment 1, matching upstream's extension. Array
strides use the padded size, so every successive element keeps its members'
relative alignment.

Python's align_to helper uses integer `//`, which expresses the integer
rounding directly; C uses integer `/`. The helper is shared by parsing and
stack-frame rounding. This commit aligns members within structs; it does not
add alignment rules for independent stack/global variables. Int is still
unlike GCC's four-byte int, and struct copying/call ABI rules are incomplete.

## Assembly and WSL example

```sh
printf 'int main(){struct {char a;int b;} x; x.b=42; return x.b;}\n' > /tmp/lesson50.c
python3 python/main.py -o /tmp/lesson50.s /tmp/lesson50.c
cat /tmp/lesson50.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson50 /tmp/lesson50.s
/tmp/lesson50
echo $?
```

Member access now emits `add $8, %rax` to reach b rather than `add $1`.
The eight-byte field load/store and epilogue are unchanged; the shell reports
42. Tests inspect field offsets, tail padding, nested structs, arrays and empty
structs, then run real programs and the updated upstream C struct fixture.

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
