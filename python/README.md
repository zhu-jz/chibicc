# Lesson 105: Global scalar and string initializers

Original chibicc commit: [`bbfe3f4369e1dd2266b827c81d7d9078ab1d301f`](https://github.com/rui314/chibicc/commit/bbfe3f4369e1dd2266b827c81d7d9078ab1d301f).
Earlier explanations are available in Git history.

## What changed

Global declarations now accept initializers. The existing initializer tree is
serialized at compile time into zero-filled bytes, recursively for arrays and
strings. Scalar expressions use the existing constant evaluator. The variable's
completed type is retained, including inferred array lengths.

Python bytearray and masked int.to_bytes explicitly encode little-endian data;
upstream writes through integer pointers into allocated memory on its host.
The generated target remains x86-64 Linux. Runtime function calls cannot supply
global initial values. Struct/union member serialization and address relocations
are not implemented by this original commit; brace-initialized global aggregates
other than arrays still remain zero at this historical step.

## Assembly and WSL example

```sh
printf 'int answer=6*7;int main(){return answer;}\n' > /tmp/lesson105.c
python3 python/main.py /tmp/lesson105.c > /tmp/lesson105.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson105 /tmp/lesson105.s
/tmp/lesson105
echo $?
```

The .data section contains answer followed by `.byte 42` and three zero bytes.
Main loads its four-byte value; there is no runtime multiplication. Exit status
is 42. Tests check every scalar width, negative-value truncation, arrays, strings,
exact byte order, nonconstant rejection, and updated upstream examples.

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
