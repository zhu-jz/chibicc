# Lesson 63: Long long as an alias for long

Original chibicc commit: [`f46370ef98adec5d3a840d69a6b34a03d80b0699`](https://github.com/rui314/chibicc/commit/f46370ef98adec5d3a840d69a6b34a03d80b0699).
Earlier explanations are available in Git history.

## What changed

The permitted type-word combinations now include two longs, with an optional
int: `long long`, `long long int`, `int long long`, and `long int long` all
select the existing LONG type. Size and alignment are both 8. No separate type
kind or codegen instruction is needed because this original step deliberately
makes long long an alias for long.

This supplies the cases missing in lesson 62's actual C switch. Three longs,
two ints, and combining short with long remain invalid. Python extends its
explicit combination table rather than C's packed keyword counter; the
accepted combinations have the same behavior. Literal typing and arithmetic
conversion limits remain at the previous stage.

## Assembly and WSL example

```sh
printf 'int main(){long long x=4294967296;return x/65536/65536;}\n' > /tmp/lesson63.c
python3 python/main.py -o /tmp/lesson63.s /tmp/lesson63.c
cat /tmp/lesson63.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson63 /tmp/lesson63.s
/tmp/lesson63
echo $?
```

The literal and full `%rax` store/load preserve the eight-byte value, and two
signed divisions return 1. The assembly is the same as for a long declaration;
the shell displays status 1 and the executable prints nothing. Tests inspect
the alias's type/size/alignment for all word orders, execute a wide stored
value, reject excess/mixed specifiers, and run the updated upstream declaration
fixture with every other C fixture.

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
