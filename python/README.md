# Lesson 198: Pass overflow arguments on the stack

Original chibicc commit: [`b29f0521025c95ff331ddb58258b1083f8efd9ff`](https://github.com/rui314/chibicc/commit/b29f0521025c95ff331ddb58258b1083f8efd9ff).
Earlier explanations are available in Git history.

Calls now use up to six general-purpose registers and eight floating registers,
then pass additional scalar arguments in eight-byte stack slots. Register
counts are independent. Stack arguments are evaluated right to left first;
register arguments follow in a second right-to-left pass. C leaves argument
evaluation order unspecified; this preserves the original two-pass choice.

Padding is reserved before argument evaluation so the final argument area ends
on a sixteen-byte boundary, including when an outer expression already has a
saved temporary. After the call the compiler removes stack arguments and
padding. It holds the function address in r10 and sets rax to the number of
floating registers used, supplying the required variadic AL value.

This commit changes callers only. Python-generated definitions still reject
parameters exceeding the register limits until their receiving logic advances.
Aggregate arguments and the bundled va_arg stack reader remain unsupported.
Tests call GCC-compiled helpers to exercise the new ABI without adding later
callee features. Python lists replace the recursive C argument-list traversal.

```sh
printf 'int sum7(int,int,int,int,int,int,int);int main(void){return sum7(1,2,3,4,5,6,21);}\n' > /tmp/lesson.c
printf 'int sum7(int a,int b,int c,int d,int e,int f,int g){return a+b+c+d+e+f+g;}\n' > /tmp/helper.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s /tmp/helper.c
/tmp/lesson
echo $?  # 42
```

The seventh integer is pushed, six others are restored into argument registers,
and the indirect call uses r10. Its result is returned in rax. Tests cover ten
integer/float/double arguments, nested-expression alignment, an external
variadic function with ten doubles, floating register count, two-pass evaluation,
existing calls and the original mixed variadic sprintf fixture.

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
