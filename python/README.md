# Lesson 196: Add va_arg and register classification

Original chibicc commit: [`5322ea8495d70be81a6b80f7a88850b85bfba240`](https://github.com/rui314/chibicc/commit/5322ea8495d70be81a6b80f7a88850b85bfba240).
Earlier explanations are available in Git history.

stdarg.h now defines va_arg using a statement expression and the parser's
`__builtin_reg_class(type)` operation. The builtin becomes a constant: 0 for
integer or pointer types, 1 for floating types, and 2 for other types. It parses
a type name and emits no runtime function call.

The header's general-purpose and floating readers return the next saved
register slot and advance the corresponding offset by eight bytes. The macro
casts that address to a pointer to the requested type and dereferences it.
These definitions are copied unchanged. They preserve the historical compact
floating save layout, perform no exhaustion checks, and leave the memory
reader unimplemented with a division-by-zero placeholder. Stack or aggregate
variadic arguments are therefore not supported at this step.

```sh
cat > /tmp/lesson.c <<'C'
#include <stdarg.h>
int sum(int fixed,...){va_list ap;va_start(ap,fixed);
int x=va_arg(ap,int);int y=va_arg(ap,int);return x+y;}
int main(void){return sum(0,7,35);}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The callee saves argument registers, reads the slots for 7 and 35, adds them
and returns the result in %rax. Tests check type classification, two integer
arguments, interleaved floating/integer/pointer arguments, malformed syntax,
existing header behavior and the original new variadic test program.

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
