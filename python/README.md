# Lesson 204: Read variadic arguments from the stack

Original chibicc commit: [`b6d3cd00df7d0496fca2af2c34e72ab3e6af4028`](https://github.com/rui314/chibicc/commit/b6d3cd00df7d0496fca2af2c34e72ab3e6af4028).
Earlier explanations are available in Git history.

Variadic prologues now initialize overflow_arg_area to rbp+16. The bundled
stdarg.h checks exhausted GP and floating save areas and reads subsequent
values from that pointer, rounding each advance to eight bytes. Large values
are read directly from memory. The header is copied verbatim from this commit.

```sh
printf '#include <stdarg.h>\nint sum(int n,...){va_list ap;va_start(ap,n);int s=0;for(int i=0;i<n;i++)s+=va_arg(ap,int);return s;}int main(void){return sum(7,1,2,3,4,5,6,21);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The first five unnamed integers use saved GP registers; the remaining two
come from the incoming stack. The assembly initializes the pointer with movq
and addq $16, then the C header's generated code updates it for each va_arg.
Tests cover ten integers, ten doubles, a stack aggregate, and the original
mixed twenty-argument example. We retain this commit's compact eight-byte
floating saves, fixed overflow starting point, and header alignment expression;
full platform va_list interoperability is not claimed at this historical step.

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
