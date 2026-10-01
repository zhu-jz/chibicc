# Lesson 95: Conditional expressions

Original chibicc commit: [`447ee098c51f6f615ef560b35d429f32f0cb5a35`](https://github.com/rui314/chibicc/commit/447ee098c51f6f615ef560b35d429f32f0cb5a35).
Earlier explanations are available in Git history.

## What changed

`condition ? true_value : false_value` evaluates its condition once and executes
only the selected branch. The parser places it below logical || and above
assignment. Its middle operand accepts a full expression (including comma), and
its last operand is another conditional expression, giving right associativity.
Nonvoid branches receive usual arithmetic conversions; if either is void, the
whole expression is void. Complete C pointer/aggregate conditional rules remain
outside this historical implementation.

Python stores the three operands in the existing cond/then/els Node fields.
The emitter generates branches and merge labels; Python's own conditional
expression does not evaluate the compiled program.

## Assembly and WSL example

```sh
printf 'int main(){return 1?42:3;}\n' > /tmp/lesson95.c
python3 python/main.py /tmp/lesson95.c > /tmp/lesson95.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson95 /tmp/lesson95.s
/tmp/lesson95
echo $?
```

The zero comparison jumps to `.L.else.N` for false. The true path loads 42 and
jumps past the else path to `.L.end.N`; only one result reaches the return.
The shell displays 42. Tests cover selected/skipped effects, guarded dereferences,
right associativity, comma parsing, int/long conversion, void branches, assembly,
malformed input, and the updated original arithmetic programs.

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
