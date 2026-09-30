# Lesson 34: String literals

Original chibicc commit: [`4cedda2dbeca6bd81d2bd00032f7cff46e0a985e`](https://github.com/rui314/chibicc/commit/4cedda2dbeca6bd81d2bd00032f7cff46e0a985e).
Earlier explanations are available in Git history.

## What changed

Quoted text becomes a STR token with raw source text, byte contents including
one terminating zero, and a char-array type. The parser creates an anonymous
global named `.L..0`, `.L..1`, etc., and returns a variable node referring to it.
The generator emits `.byte` entries instead of `.zero` for initialized data.

`"abc"` occupies four bytes: 97, 98, 99, 0. Array conversion leaves its address
in `%rax`; subscripting adds a byte offset and uses the signed char load.
`sizeof("abc")` is 4. Empty strings still have their terminating byte.
Unclosed strings and raw newlines inside them are errors. Escape decoding is
not supported in this original step.

## Run it

```sh
python3 python/main.py 'int main(){return "abc"[1];}' > /tmp/lesson34.s
cat /tmp/lesson34.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson34 /tmp/lesson34.s
/tmp/lesson34
echo $?
```

The executable prints nothing; the last command shows **98**, the byte for b.
Use an interactive shell without `set -e` for nonzero statuses. Tests include
all upstream strings, terminators, sizes, data bytes, addressing, UTF-8 size,
and unclosed strings.

Python encodes literal text as UTF-8, matching bytes supplied through a UTF-8
Linux command line. Byte values are printed unsigned (0–255), whereas upstream
may print signed C chars; these `.byte` values assemble to the same bits.
Diagnostics still count Python characters. Anonymous counters belong to a
parser instance rather than a C static variable. Strings remain writable data,
matching upstream's current emission; no string pooling or new syntax is added.

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
