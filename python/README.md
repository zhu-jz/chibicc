# Lesson 156: Compile multiple input files

Original chibicc commit: [`b833cd0f297ba7979c23cff1b88c27beb4f2f737`](https://github.com/rui314/chibicc/commit/b833cd0f297ba7979c23cff1b88c27beb4f2f737).
Earlier explanations are available in Git history.

## What changed

The driver collects input paths in a Python list and compiles each file separately.
Each child gets explicit -cc1-input and -cc1-output options so it selects the right
translation unit even though the copied command line contains every input.
Default output names use each basename; multiple inputs with a single -o are
rejected. This step produces separate objects or assembly files and does not link.

Option arguments are checked before processing help, matching the original -o
precheck. Python also checks the new internal option arguments and missing
-cc1-input explicitly, giving readable errors where C would use a null pointer.
Temporary assembly files are cleaned up after each source is assembled.

## Assembly and WSL example

```sh
printf 'int f(void);int main(void){return f();}\n' > /tmp/lesson156-main.c
printf 'int f(void){return 42;}\n' > /tmp/lesson156-answer.c
(cd /tmp && python3 /home/zhu/chibicc/python/main.py lesson156-main.c lesson156-answer.c)
gcc -static -Wl,-z,noexecstack -o /tmp/lesson156 /tmp/lesson156-main.o /tmp/lesson156-answer.o
/tmp/lesson156
echo $?
```

The first object contains an indirect call to external f; the second defines f
and returns 42. Linking resolves the address, and the executable exits with 42.
Tests check both objects, their linked execution, separate .s outputs and source
metadata, ambiguous -o rejection, option validation, and the original examples.

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
