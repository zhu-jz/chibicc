# Lesson 40: Read source files and report line locations

Original chibicc commit: [`d9ea59757e2710e34f105e98230f30f578e0e662`](https://github.com/rui314/chibicc/commit/d9ea59757e2710e34f105e98230f30f578e0e662).
Earlier explanations are available in Git history.

## What changed

The command line now takes a filename, not source text. A filename of `-`
reads standard input. Input is read completely and a final newline is added
if missing, matching upstream. In-memory tokenization remains available for
unit tests; the driver explicitly passes file contents to the tokenizer.

Diagnostics now show `filename:line: source line` followed by a caret and
message. The driver finds the line containing the error and adds the filename
prefix width to the caret indentation. Only that line is printed, not the
whole translation unit. File-opening failures have a plain error message.

## Run it

```sh
printf 'int main(){return 42;}\n' > /tmp/lesson40.c
python3 python/main.py /tmp/lesson40.c > /tmp/lesson40.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson40 /tmp/lesson40.s
/tmp/lesson40
echo $?
printf 'int main(){return 42;}\n' | python3 python/main.py -
```

The executable prints nothing; `echo $?` shows **42**. Use an interactive shell
without `set -e` for nonzero statuses. The final pipeline prints the same
assembly through stdin. Code generation is unchanged in this commit.

The complete suite now supplies source through stdin. Tests also check files
with spaces in their names, final-newline normalization, a filename/line/caret
diagnostic on line 2, missing files, and invalid encoding.

Python uses standard file I/O and explicit driver state instead of C memory
streams and tokenizer globals. Files are decoded as UTF-8; invalid UTF-8 is
reported cleanly. Newline bytes are preserved in named files. Python's EOF
location handling is bounded, avoiding upstream's possible read past its buffer
when reporting an error exactly at EOF. Carets still count characters rather
than bytes, with the same simple space indentation used by upstream.

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
