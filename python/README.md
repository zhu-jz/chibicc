# Lesson 315: Document the compiler and its design

Original chibicc commit: [`982041fb1c78147951e73050a6c87059f92ea4e6`](https://github.com/rui314/chibicc/commit/982041fb1c78147951e73050a6c87059f92ea4e6).
Earlier explanations are available in Git history.

This original commit changes only documentation. It describes chibicc's
incremental teaching approach, compiler stages, supported features, and preference
for readable code. The Python lesson updates this README; compiler behavior is
unchanged. Previous lesson explanations remain available in Git history.

The port follows the same stages:

1. `tokenizer.py` reads source, normalizes it and creates tokens with locations.
2. `preprocess.py` handles includes, conditional directives and macro expansion.
3. `parse.py` builds syntax trees; `type.py` annotates them, and `constexpr.py`
   evaluates C constant expressions using explicit C arithmetic rules.
4. `codegen.py` assigns storage and emits x86-64 Linux assembly. `main.py` drives
   compilation, invokes the assembler/linker and handles command-line options.

Lists and dataclasses keep the implementation direct. Each grammar production
has an ordinary parser function, and assembly generation remains explicit.
There is no optimizer. This project targets x86-64 Linux/WSL; it does not promise
portability to Windows executables or other instruction sets.

The accumulated lessons cover arithmetic/control flow, functions, structures and
unions, bitfields, designated initialization, floating point including x87 long
double, macros, Unicode identifiers/strings, VLAs, alloca, variadic calls, thread
local storage, atomics, PIC, and linker/dependency options. The driver can build
executables, objects, static links, and shared libraries. Complex arithmetic,
K&R definitions and GCC extended assembly are not implemented.

Historical limitations are intentionally retained: atomic fetch macros return
updated values, fence/order macros have limited semantics, packed-member atomics
keep the earlier lowering, include-next uses a shared search cursor, and some
long-double initializer/ABI cases remain unsupported. This is an educational
history port, not a claim of complete C11 conformance.

```sh
cat >/tmp/lesson.c <<'C'
struct Pair { int first, second; };
int sum(struct Pair value) { return value.first + value.second; }
int main(void) { return sum((struct Pair){20, 22}); }
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Inspect `/tmp/lesson.s` to see the structure argument passed through the System V
register convention, integer additions, and the return accumulator. The program
returns a status; `echo $?` displays it. Linux exposes its low eight bits.

`make -C python test-all` runs the source implementation and the packaged Python
archive. The archive packages Python modules; it is not C self-hosting. The
optional `thirdparty.py` workflows pin Git, libpng, SQLite, TinyCC and CPython.
Their full external suites have not been run for this port; upstream's success
claims apply to its C implementation. For a command preview use, for example,
`python3 python/thirdparty.py git --dry-run`.

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
