# Lesson 138: Unnamed prototype parameters

Original chibicc commit: [`1fad2595d6fa67e57cd795d4faac4306e42e72c5`](https://github.com/rui314/chibicc/commit/1fad2595d6fa67e57cd795d4faac4306e42e72c5).
Earlier explanations are available in Git history.

## What changed

Declarators may now omit their identifier, allowing prototypes such as
`int f(int, char *);`. Types record name_pos even when name is absent. Variable,
typedef, function and definition-parameter contexts explicitly require names
and report the appropriate missing-name diagnostic. Prototype parameters need
only their types.

Python uses optional Token fields and preserves name_pos during array-to-pointer
parameter adjustment; that gives a readable error for an omitted array parameter
name instead of dereferencing a null diagnostic token. Representative object
token metadata is added as upstream does, ready for later uses. There are no
changes to argument passing or type conversion.

## Assembly and WSL example

```sh
printf 'int f(int);int main(void){return f(42);}int f(int x){return x;}\n' > /tmp/lesson138.c
python3 python/main.py /tmp/lesson138.c > /tmp/lesson138.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson138 /tmp/lesson138.s
/tmp/lesson138
echo $?
```

The prototype emits no function body. Main passes 42 in edi, and the later named
parameter definition returns it, giving exit status 42. Tests cover unnamed
scalar/pointer/array prototypes, preserved token positions, required-name errors,
updated declaration diagnostics, emitted calls, execution, and original C code.

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
