# Lesson 71: Function argument conversions

Original chibicc commit: [`fdc80bc6b5faa058b88d838332c71b7101712896`](https://github.com/rui314/chibicc/commit/fdc80bc6b5faa058b88d838332c71b7101712896).
Earlier explanations are available in Git history.

## What changed

Call nodes now retain the whole declared function type. Arguments corresponding
to named parameters are wrapped in casts to those parameter types. This widens
negative ints to signed longs before passing them in 64-bit registers, and
converts narrow integer arguments. Struct/union parameters explicitly report
that passing aggregates is unsupported. Arguments beyond the declared list
remain unconverted, and arity checking is still incomplete, as in this commit.

Python uses list indices to walk the parameter types alongside arguments; C
walks linked lists. Runtime and tree tests check conversions and function metadata.

## Assembly and WSL example

```sh
printf 'int f(long a,long b){return a/b;}int main(){return f(-10,2)==-5;}\n' > /tmp/lesson71.c
python3 python/main.py /tmp/lesson71.c > /tmp/lesson71.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson71 /tmp/lesson71.s
/tmp/lesson71
echo $?
```

`movsxd %eax, %rax` sign-extends an int argument before it reaches rdi/rsi.
Inside f, `cqo` and `idiv %rdi` perform signed 64-bit division. Main's comparison
returns 1. The compiler emits these instructions; GCC assembles and links them.

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
