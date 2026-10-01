# Lesson 126: Small function return values

Original chibicc commit: [`dcd45792264795a32f19581a904dda8bf6d3ad06`](https://github.com/rui314/chibicc/commit/dcd45792264795a32f19581a904dda8bf6d3ad06).
Earlier explanations are available in Git history.

## What changed

After a call returning _Bool, char or short, the emitter now extracts the
meaningful low byte or word. Bool uses zero extension from al; signed char and
short use sign extension from al or ax into eax. Later conversions can then
safely use the normalized result rather than unrelated high register bits.

Python selects instructions from the call node's declared return type, exactly
as upstream. The C ABI does not require every high bit of rax to hold a useful
value for these small return types. The upstream tests deliberately use helper
functions with int return definitions and small return declarations to expose
that issue; the port preserves those educational fixtures.

## Assembly and WSL example

```sh
printf 'char f(void);int main(){return f()<0;}\n' > /tmp/lesson126.c
printf 'int f(void){return 0x2ff;}\n' > /tmp/lesson126-helper.c
python3 python/main.py /tmp/lesson126.c > /tmp/lesson126.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson126 /tmp/lesson126.s /tmp/lesson126-helper.c
/tmp/lesson126
echo $?
```

After call f, `movsbl %al,%eax` interprets low byte ff as signed -1. The comparison
is true, so exit status is 1. Tests cover garbage high bits for all three return
kinds, signed comparisons and long conversion, exact cleanup instructions,
execution, and updated original function/helper examples.

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
