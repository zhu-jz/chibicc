# Lesson 45: Tests written in C

Original chibicc commit: [`cd832a311e56bda981c9c957ba45f1bc1f6cc737`](https://github.com/rui314/chibicc/commit/cd832a311e56bda981c9c957ba45f1bc1f6cc737).
Earlier explanations are available in Git history.

## What changed

Upstream moves tests into C programs grouped by arithmetic, control flow,
functions, pointers, strings, and variables. This commit changes no compiler
behavior. Matching snapshots are now in `python/test/`, alongside `test.h`'s
ASSERT macro and the small assertion helper `common`. The existing Python
assembly and diagnostic tests remain useful and are retained.

`test_upstream_c_programs` asks GCC to preprocess each test, feeding the result
to our Python compiler through stdin. GCC expands `ASSERT(expected, expr)`
into `assert(expected, expr, "expr")`, including macro stringification. Our
compiler emits the test program's assembly. GCC then assembles/links it with
the helper, and the harness executes it with a timeout. This compiler still
has no preprocessor: GCC preprocessing is test preparation only, following
upstream's test workflow. The original C compiler is never invoked.

The helper compares full integer results and prints each assertion. This
avoids relying only on the operating system's eight-bit exit status and lets
one executable check many expressions. MIT attribution applies to these
upstream test snapshots as well as the port.

## Run and understand the assembly

```sh
python3 python/test.py ExpressionCompilerTests.test_upstream_c_programs
printf 'int main(){return 42;}\n' > /tmp/lesson45.c
python3 python/main.py -o /tmp/lesson45.s /tmp/lesson45.c
gcc -static -Wl,-z,noexecstack -o /tmp/lesson45 /tmp/lesson45.s
/tmp/lesson45
echo $?
```

The compiler's instructions are unchanged: the example moves 42 into `%rax`
and returns through the shared epilogue, so the shell displays 42. The test
programs also move call arguments into `%rdi`, `%rsi`, and `%rdx`, then execute
`call assert`. Their output comes from the linked helper's printf, not from
the compiler. Upstream's six C programs must all finish with status zero and
print their final `OK`.

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
