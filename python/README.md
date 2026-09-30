# Lesson 42: Output files and command-line help

Original chibicc commit: [`a0388bada4016bc0c3be6154c159faf80ce18d01`](https://github.com/rui314/chibicc/commit/a0388bada4016bc0c3be6154c159faf80ce18d01).
Earlier explanations are available in Git history.

## What changed

The driver accepts `-o path`, joined `-opath`, and `--help`. Input is still a
filename, with `-` selecting stdin. Output defaults to stdout; `-o -` also
selects stdout. Help prints usage to stderr and exits successfully. A missing
output path prints usage and fails; unknown options and missing input produce
plain errors.

The argument scanner follows upstream's small manual parser: options may appear
before or after the input, and the last input/output argument wins. It does not
combine multiple input files. The Python driver selects the output destination
after generating its assembly string. C instead passes a FILE pointer into the
generator. This deliberate difference retains buffered output: a compilation
error neither emits partial assembly nor overwrites an existing output file.

## Run it in WSL

With Python 3 and GCC (`build-essential` on Ubuntu), run from the repository root:

```sh
printf 'int main(){return 42;}\n' > /tmp/lesson42.c
python3 python/main.py -o /tmp/lesson42.s /tmp/lesson42.c
cat /tmp/lesson42.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson42 /tmp/lesson42.s
/tmp/lesson42
echo $?
python3 python/main.py --help
```

The executable prints nothing; `echo $?` immediately afterward displays **42**.
Use an interactive shell without `set -e` for nonzero statuses. `-o` writes
assembly; GCC assembles and links it into an executable. The body contains
`mov $42,%rax` and a jump to `.L.return.main`; cleanup restores `%rbp` and
executes `ret`. No machine-code or assembly-generation change is needed for
this original driver commit.

Stdin and joined output forms also work:

```sh
printf 'int main(){return 42;}\n' | python3 python/main.py -o/tmp/lesson42.s -
python3 python/main.py -o - /tmp/lesson42.c
```

## Tests and current limits

Driver tests cover both upstream checks (output creation for empty input and
help), separated/joined options, paths with spaces, stdin/stdout destinations,
empty output, invalid options, output errors, and preserving output on compile
failure. The full suite retains assembly, diagnostic, and executable checks.

The current compiler supports functions with up to six parameters/arguments,
int/char variables, pointers, arrays, string literals and escapes, arithmetic,
comparisons, assignments, returns, if/else, for/while, sizeof expressions, and
GNU statement expressions. Ints and pointers still occupy eight bytes, chars
one. Globals have no general initializer syntax. Function signatures and
assignment conversions are incomplete, names still use function-wide scope,
and calls do not yet adjust for temporary-stack alignment. Bounds and runtime
memory accesses are unchecked. Decimal tokens are checked to fit 0 through
2147483647. Input files use UTF-8 and diagnostics count characters.

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
