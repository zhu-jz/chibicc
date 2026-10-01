# Lesson 265: Emit common symbols for tentative globals

Original chibicc commit: [`85e46b1071b54649740b35df939f32ed188c0e13`](https://github.com/rui314/chibicc/commit/85e46b1071b54649740b35df939f32ed188c0e13).
Earlier explanations are available in Git history.

File-scope definitions without an initializer now become tentative. Assembly
emits `.comm name,size,alignment`, allowing the linker to combine common symbols
or replace one with an initialized definition from another translation unit.
Within a file, a scan discards a tentative object when another definition of the
same name exists. Extern declarations alone do not allocate storage.

```sh
printf 'int x;int x=42;int main(void){return x;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Only the initialized x is emitted in .data; main loads it through its RIP-relative
address and returns 42. Tests also inspect common-symbol assembly and nm's C
symbol class, run zero-initialized globals, link against an initialized GCC helper,
and execute the original commonsym.c fixture. Static common objects remain local.
Python filters an object-list snapshot instead of relinking C's global list.
The original predicate has a bug: two tentative definitions can both be removed.
We retain that predicate and test it; snapshot filtering avoids C's incidental
order changes from relinking during the scan. Existing BSS snapshots are updated
for common symbols; explicitly initialized zero values remain in .data.

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
