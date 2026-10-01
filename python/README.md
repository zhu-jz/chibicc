# Lesson 266: Choose common or BSS global definitions

Original chibicc commit: [`6d344ed9459bd0328de53a58505a397d92cb0c8a`](https://github.com/rui314/chibicc/commit/6d344ed9459bd0328de53a58505a397d92cb0c8a).
Earlier explanations are available in Git history.

The driver now accepts -fcommon and -fno-common, with the last option winning.
The default remains common-symbol emission. With -fno-common, a tentative global
instead gets an ordinary label and zero-filled .bss storage, so duplicate global
definitions across translation units produce a linker error.

```sh
printf 'int x;int main(void){x=42;return x;}\n' > /tmp/lesson.c
python3 python/main.py -fno-common -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly emits x in .bss, stores 42 through its RIP-relative address, then loads
and returns it. Tests inspect both assembly forms and option ordering, link
repeated globals successfully with -fcommon, and verify the real linker rejects
them with -fno-common. Original fixtures continue to use the common default.
Python passes the option explicitly into CodeGenerator rather than exposing
C's global opt_fcommon. Tentative-object scanning is unchanged by the flags,
including its previously explained historical duplicate-removal limitation.

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
