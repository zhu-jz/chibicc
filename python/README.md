# Lesson 41: Assembly line-output refactor

Original chibicc commit: [`7b8528f71c78a01e8ff41a76a83a320d1ef80e93`](https://github.com/rui314/chibicc/commit/7b8528f71c78a01e8ff41a76a83a320d1ef80e93).
Earlier explanations are available in Git history.

## What changed

Upstream adds a `println()` helper and replaces formatted printing calls that
manually append newlines. The original commit explicitly makes no functional
change. Python already collects complete lines in `CodeGenerator.assembly`,
then joins them with `"\n"`; the driver writes the result with its final newline.
We retain that straightforward equivalent instead of adding another wrapper.

This intentional implementation difference also preserves the existing buffered
output behavior: a compilation error produces no partial assembly. Each list
item is an instruction, directive, or label, and line termination is centralized
at the join rather than repeated throughout the generator.

## Run it

```sh
printf 'int main(){return 42;}\n' | python3 python/main.py - > /tmp/lesson41.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson41 /tmp/lesson41.s
/tmp/lesson41
echo $?
```

The executable prints nothing; the last command shows **42**. Use an interactive
shell without `set -e` for nonzero statuses. File and stdin input use the same
parser and generator. The assembly body still moves 42 into `%rax` and jumps
to `.L.return.main`, which restores the frame and executes `ret`.

The exact-assembly regression suite and control-flow tests verify unchanged
line contents and termination. The compiler's generator is unchanged in this
port's commit; only lesson documentation and provenance advance. No syntax,
types, or calling-convention changes are introduced.

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
