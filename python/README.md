# Lesson 316: Member access on assignment and conditional results

Original chibicc commit: [`90d1f7f199cc55b13c7fdb5839d1409806633fdb`](https://github.com/rui314/chibicc/commit/90d1f7f199cc55b13c7fdb5839d1409806633fdb).
Earlier explanations are available in Git history.

This is the final commit in the original history present in this repository.
It permits member access on structure/union assignment and conditional results:
`(x = y).member`, `(condition ? x : y).member`, and nested member access.

The parser already creates these expression trees. Previously `gen_addr` did
not recognize their aggregate base and reported `not an lvalue`. It now delegates
aggregate `ASSIGN` and `COND` nodes to `gen_expr`. This compiler represents an
aggregate expression result by an address in `%rax`: assignment copies bytes
while preserving its source address, and a conditional computes only its chosen
branch. Member access adds its byte offset and loads the member from that
address. Scalar assignment expressions retain their previous address diagnostic.

```sh
cat >/tmp/lesson.c <<'C'
struct Pair { int first, second; };
int main(void) {
  struct Pair x = {1, 2}, y = {20, 22};
  int first = (x = y).first;
  return first + (1 ? x : y).second;
}
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42; the executable itself prints nothing
```

Tests cover structures and unions, both conditional branches, copied destination
values, nested members, branch side effects and aggregate function results. The
original structure fixture includes the three new examples unchanged. Python
adds the same address-generation case without introducing another representation
or changing the earlier byte-copy strategy.

The compiler is now at original commit `90d1f7f199cc55b13c7fdb5839d1409806633fdb`.
Its stages remain tokenization, preprocessing, parsing/type checking/constant
expressions, and x86-64 Linux code generation. `main.py` drives the assembler and
linker. There is no optimizer. Historical limitations remain, including atomic
fetch/order/fence semantics, some long-double initializer/ABI cases, and the
shared include-next cursor. This is an educational port, not a claim of complete
C11 conformance or portability beyond x86-64 Linux/WSL.

`make -C python test-all` checks both the source implementation and the packaged
Python archive, including copied original C tests. The archive packages Python
modules; it does not self-host through the original C compiler. Optional pinned
third-party workflows are available through `thirdparty.py`; their full external
application suites have not been run for this port. Earlier explanations live
in Git history, with one Python commit recording each original commit.

## Matching the original compiler binary

The Python compiler can compile the original nine C source files into the same
complete executable as the C compiler, including assertions, debug information,
symbols and the linker build ID. Run the comparison on x86-64 Linux/WSL:

```sh
make -C python test-bootstrap
cmp python/build/bootstrap/reference/chibicc python/build/bootstrap/python-1/chibicc
cmp python/build/bootstrap/reference/chibicc python/build/bootstrap/python-2/chibicc
```

`bootstrap.py` first builds the original compiler with GCC, then uses that C
compiler and both the Python source and packaged compiler to compile the same
original C files. It reuses identical assembly, object and linker paths and
compares every complete object file and the linked executable. It checks debug
line directives, retained debug sections and assertion references, runs the
compiled compiler's hash-map test, and compiles a program that exits with 42.
Artifacts and the JSON report stay in `python/build/bootstrap/`. To compare an
existing reference too, add `--existing /path/to/chibicc` when invoking
`python3 python/bootstrap.py` from the repository root.

Two implementation details matter for byte identity. The original C
preprocessor reuses argument tokens: expanding an ordinary parameter can
rewrite links visible to a later `#parameter`. For example, with `VALUE` defined
as `7`, `BOTH(x)` defined as `x, #x` produces `1 + 7, "1 + 7"` for
`BOTH(1 + VALUE)`, but `7, "VALUE"` for `BOTH(VALUE)`. Python now preserves this
historical quirk with a small map of argument-token links. This intentionally
differs from the usual C rule that `#` uses the unexpanded argument spelling.
The parser also retains the original empty VLA-size expression nodes for
ordinary local declarations and pointer types. They generate no instructions,
but their `.loc` directives affect debug information.

No assertions or debug data are removed. Byte identity requires the same source
paths, working directory, headers, assembler, linker and flags for both builds;
different toolchains or paths can change the resulting bytes. Assembly text can
still differ in harmless formatting, such as signed versus unsigned `.byte`
values, while producing identical objects. This check is a post-history fidelity
fix; the current original lesson remains 316.

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
