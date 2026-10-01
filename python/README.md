# Lesson 92: Continue statements

Original chibicc commit: [`3c83dfd8af045ae6923d4ccb3a3a5a50f4012346`](https://github.com/rui314/chibicc/commit/3c83dfd8af045ae6923d4ccb3a3a5a50f4012346).
Earlier explanations are available in Git history.

## What changed

Every for/while loop now has both a break label and a continue label. The emitter
places continue after the body and before the increment. `continue;` becomes a
GOTO to that label: a for loop still runs its increment, while a while loop jumps
back to test its condition. Nested loops save and restore both parser targets,
and a continue outside a loop reports `stray continue`.

Python uses parser attributes and Node fields for these targets, replacing C's
globals and struct members. Continue uses the existing jump emitter. This remains
an educational snapshot of this original commit, with the earlier conversion,
aggregate-passing, and declaration limitations preserved.

## Assembly and WSL example

```sh
printf 'int main(){int sum=0;for(int i=0;i<10;i++){if(i>5)continue;sum++;}return sum;}\n' > /tmp/lesson92.c
python3 python/main.py /tmp/lesson92.c > /tmp/lesson92.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson92 /tmp/lesson92.s
/tmp/lesson92
echo $?
```

continue emits `jmp .L..N` to the label before i's increment. Only i=0 through 5
increase sum, so main returns 6. The executable prints nothing; `echo $?` displays
its exit status. Tests cover for increments, while condition reevaluation, nested
and restored targets, skipped bodies, stray continue, emitted target positions,
and all updated upstream programs.

This is the fiftieth lesson in the requested batch (lessons 43–92). Each original
commit has its own Python commit and its corresponding README explanation in Git
history. To read a previous explanation, use `git show <python-commit>:python/README.md`.
The complete regression suite is run at this final step.

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
