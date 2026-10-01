# Lesson 267: Address variables relative to the current thread

Original chibicc commit: [`b3772845bd07fb695ca6b6e67ad7640776ae0f6c`](https://github.com/rui314/chibicc/commit/b3772845bd07fb695ca6b6e67ad7640776ae0f6c).
Earlier explanations are available in Git history.

File-scope _Thread_local and GNU __thread declarations now mark TLS objects.
Their addresses use the Linux thread pointer in fs:0 plus a linker-resolved
tpoff offset. Initialized objects go in .tdata and zero-filled objects in .tbss;
TLS definitions bypass tentative/common-symbol treatment. __STDC_NO_THREADS__
is removed from predefined macros, matching the original commit.

```sh
printf '_Thread_local int x=42;int main(void){return x;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -pthread -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly reads fs:0 into rax, adds x@tpoff and loads x from that address. Each
thread has its own storage initialized from the TLS image. Tests inspect both
sections and address instructions, run both keywords, and create/join a real
pthread that changes its copy while main's copy remains 42. The original tls.c
also checks a shared ordinary global. Runtime test linking now uses -pthread.
Python carries an is_tls flag on objects and declaration attributes instead of C
struct fields. This step implements the original local-exec TLS model for Linux
executables. Block-scope static TLS handling and dynamic-library TLS models are
not extended beyond this original patch.

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
