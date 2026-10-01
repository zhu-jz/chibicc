# Lesson 171: Add #ifdef and #ifndef

Original chibicc commit: [`1f80f581e517ae4a5df6ab38af48a0d2a1089c73`](https://github.com/rui314/chibicc/commit/1f80f581e517ae4a5df6ab38af48a0d2a1089c73).
Earlier explanations are available in Git history.

`#ifdef NAME` includes its branch when the name has a current macro definition;
`#ifndef NAME` includes it when no definition exists. Empty replacement bodies
still count as definitions. The name is looked up directly without expansion.
Both directives use the existing conditional stack and support alternatives.

Skipping now recognizes all three opening directives. Header guards work by
combining `#ifndef` with `#define`, so repeated includes can discard an already
processed header. This original commit treats a non-identifier operand as an
undefined name; the Python port preserves that behavior rather than adding a
later validation rule.

```sh
printf '#define PRESENT\n#ifdef PRESENT\nint main(void){return 42;}\n#endif\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

Only the selected `main` reaches code generation. Assembly puts 42 in `%rax`
and returns through its frame cleanup. Tests cover both directives, empty
macros, undefinition, nested skips, the historical operand behavior and a
header included twice with a guard.

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
