# Lesson 57: Eight-byte long values

Original chibicc commit: [`43c2f0829f7d4ec3b96132b9964a778ff816b2eb`](https://github.com/rui314/chibicc/commit/43c2f0829f7d4ec3b96132b9964a778ff816b2eb).
Earlier explanations are available in Git history.

## What changed

Long has size/alignment 8; int remains 4 and char 1. Long variables, parameters,
arrays and members use the existing eight-byte loads, stores, argument-register
saves and pointer scaling. Numeric token/tree values now support wider literals.
Python's integers already had the needed representation; its decimal input
check now permits 0 through 9223372036854775807. Generated assembly interpolates
that value directly into `mov $value, %rax`; the assembler chooses its encoding.

Upstream temporarily assigns long type to every numeric literal, comparison
and function call, so `sizeof(1)`, `sizeof(1==2)`, and `sizeof(missing())` each
produce 8. A declared int variable still has size 4. Arithmetic type conversion
and function-call signature handling remain incomplete at this stage; these
intermediate choices are intentionally retained. Short becomes a reserved
keyword in this original commit but its type is not yet accepted.

The Python port keeps a clear error for literals outside the signed sixty-four
bit positive range rather than reproducing C strtoul's overflow/wrapping
behavior. Larger positive input and the unsigned spelling of the minimum
signed value are rejected. Negative expressions use unary minus as before.

## Assembly and WSL example

```sh
printf 'int main(){long x=4294967296;return x/65536/65536;}\n' > /tmp/lesson57.c
python3 python/main.py -o /tmp/lesson57.s /tmp/lesson57.c
cat /tmp/lesson57.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson57 /tmp/lesson57.s
/tmp/lesson57
echo $?
```

`mov $4294967296, %rax` constructs the large value. A full `%rax` store and
load preserve it in x. Two signed divisions reduce it to 1; the shell reports
status 1. Tests cover the largest accepted literal, large globals and function
parameters/returns, array strides, struct alignment, sizeof's intermediate
long typing, assembly widths, and range/short diagnostics. Updated upstream
function, struct and variable fixtures are run with all other C fixtures.

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
