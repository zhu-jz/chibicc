# Lesson 296: Generate position-independent code with -fPIC

Original chibicc commit: [`86785fceb169bc754efe3f29a9b63137f5c9a106`](https://github.com/rui314/chibicc/commit/86785fceb169bc754efe3f29a9b63137f5c9a106).
Earlier explanations are available in Git history.

-fpic and -fPIC enable position-independent addresses for functions and globals.
The compiler loads their addresses through GOTPCREL entries. Thread-local addresses
use the general-dynamic TLS sequence, calling __tls_get_addr through the PLT.
Local variables and allocated VLAs still use their normal frame-relative storage.

```sh
printf 'int answer=42;int main(void){return answer;}\n' > /tmp/lesson.c
python3 python/main.py -fPIC -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Assembly loads answer's address with mov answer@GOTPCREL(%rip),%rax, then reads
its value. GOT entries let the loader choose addresses without rewriting this
instruction's text. Tests assemble genuine shared libraries containing a global
reference and TLS, link them with a GCC-built caller, and run them for both flags.
Python passes a boolean into the code generator instead of using C's global
opt_fpic. The TLS prefixes and linker relocation spelling follow the original.
This step adds PIC generation; a compiler-driver -shared option is not added yet.

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
