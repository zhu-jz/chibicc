# Lesson 199: Receive stack-passed parameters

Original chibicc commit: [`9021f7f5decea3e7954f138e9bac4cfea26292be`](https://github.com/rui314/chibicc/commit/9021f7f5decea3e7954f138e9bac4cfea26292be).
Earlier explanations are available in Git history.

Function definitions now recognize parameters whose register class is full.
They assign those parameters positive frame offsets, beginning at rbp+16:
the return address and saved frame pointer occupy the preceding words. Each
following parameter starts on an eight-byte boundary. Locals and parameters
received in registers retain negative offsets in the callee's allocated frame.

The prologue saves only register parameters; stack parameters are accessed
directly in the incoming argument area. This completes scalar caller/callee
stack support from the preceding lesson. Python recomputes negative offsets
when generating the same tree again, so repeated generation retains the frame
size; the original C code assumes one generation pass. Aggregate argument
classification and the bundled variadic stack reader still await their own steps.

```sh
printf 'int sum7(int a,int b,int c,int d,int e,int f,int g){return a+b+c+d+e+f+g;}int main(void){return sum7(1,2,3,4,5,6,21);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The caller pushes the seventh value. In sum7, its address is rbp+16; the other
six values are loaded from saved local slots. Addition leaves 42 in rax before
return. Tests cover ten integer/float/double parameters, GCC callers, small
stack parameters, offsets, frame size, repeat generation, existing definitions
and the upstream mixed-register/stack functions.

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
