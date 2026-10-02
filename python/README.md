# Lesson 312: Reuse function declarations and diagnose redefinitions

Original chibicc commit: [`395308c77b94fc16b146c01cc1316b9a07635686`](https://github.com/rui314/chibicc/commit/395308c77b94fc16b146c01cc1316b9a07635686).
Earlier explanations are available in Git history.

Function declarations now reuse an existing global function object. A prototype,
a later definition, and a subsequent prototype all refer to one object, so a
prototype after a definition no longer hides the emitted function. A second
body is rejected with `redefinition of name`; an explicitly static declaration
after a non-static function declaration also receives a diagnostic.

The first declaration supplies the stored type and linkage. This commit does
not add general signature-compatibility checks. The existing `find_func` filters
out non-function objects, so the new different-kind error branch remains
unreachable for a previous variable, just as in the original helper.
Python reports errors with `CompileError` rather than C's formatted error call.

```sh
cat >/tmp/lesson.c <<'C'
int answer(void);
int answer(void) { return 42; }
int answer(void);
int main(void) { return answer(); }
C
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

The output contains one `answer:` body. `main` calls its address, receives 42 in
the accumulator, and returns it. Tests check object reuse, exactly one assembly
body, a prototype following a body, retained static linkage, and both diagnostics.

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
