# Lesson 80: Integer literal bases

Original chibicc commit: [`7df934d2b63727d67d1c054975893930fa6aff44`](https://github.com/rui314/chibicc/commit/7df934d2b63727d67d1c054975893930fa6aff44).
Earlier explanations are available in Git history.

## What changed

Integer tokens recognize decimal, a leading zero for octal, 0x/0X for hexadecimal,
and 0b/0B for binary. The reader consumes valid digits and reports `invalid digit`
at a following ASCII letter or digit that cannot belong to the literal. All
spellings become ordinary numeric nodes; assembly depends on the value rather
than the source base. Binary literals follow this compiler's extension to C.

Python's int(text, base) only converts a validated token; it does not evaluate C
expressions. We retain the earlier explicit signed-64-bit range error rather
than copying strtoul's platform overflow/wrap behavior. Integer suffixes remain
unsupported in this commit.

## Assembly and WSL example

```sh
printf 'int main(){return 0x2a;}\n' > /tmp/lesson80.c
python3 python/main.py /tmp/lesson80.c > /tmp/lesson80.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson80 /tmp/lesson80.s
/tmp/lesson80
echo $?
```

0x2a becomes `mov $42, %rax`, exactly like decimal 42. The shell displays the
exit status 42. Tests cover every base and uppercase prefix, token spelling,
invalid digit positions, assembly, executable statuses, and the original literal
test program alongside the existing fixtures.

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
