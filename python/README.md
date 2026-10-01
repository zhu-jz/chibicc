# Lesson 269: Choose the input language explicitly

Original chibicc commit: [`ee0a951b30646023ccc9a144afb4b380bf8d09b1`](https://github.com/rui314/chibicc/commit/ee0a951b30646023ccc9a144afb4b380bf8d09b1).
Earlier explanations are available in Git history.

The driver accepts attached or separate -x c, -x assembler and -x none forms.
C and assembler override the filename extension; none restores extension-based
selection. Object files ending in .o always retain their object-file role.
Stdin now requires -xc or -x assembler because it has no recognized extension.

```sh
printf 'int main(void){return 42;}\n' > /tmp/lesson.data
python3 python/main.py -xc -S -o /tmp/lesson.s /tmp/lesson.data
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Despite the .data suffix, the input is parsed as C and assembly loads and returns
42. Tests compile C under an arbitrary suffix, assemble stdin into a real ELF
object, link that object even with -xc present, reset with -x none and reject
unknown languages. Existing stdin tests now pass -xc, matching original driver
fixture changes. Python uses descriptive strings instead of C's FileType enum.
The original driver stores one final language value for every input, rather than
tracking -x state separately for each input path. The earlier assembly-input
linking omission is unchanged by this step.

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
