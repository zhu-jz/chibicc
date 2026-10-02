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
