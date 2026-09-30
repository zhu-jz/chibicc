# Lesson 91: Break statements

Original chibicc commit: [`b3047f2317b74f19fb44dfe5e577d586d93dfa3c`](https://github.com/rui314/chibicc/commit/b3047f2317b74f19fb44dfe5e577d586d93dfa3c).
Earlier explanations are available in Git history.

## What changed

Each for/while loop receives a parser-generated exit label. The parser saves the
outer break target while reading an inner loop and restores it afterward, so
break exits the innermost loop. It becomes a GOTO node with an already-resolved
label and needs no user-label lookup. A break outside a loop reports `stray break`.
Normal loop-condition failure jumps to the same exit label.

Python stores the current target on the parser and the final target on the loop
node. Anonymous labels share the existing parser counter with strings and user
labels; the emitter's begin-label counter remains separate. Continue statements
and switches are not part of this original commit.

## Assembly and WSL example

```sh
printf 'int main(){int i=0;for(;;i++){if(i==42)break;}return i;}\n' > /tmp/lesson91.c
python3 python/main.py /tmp/lesson91.c > /tmp/lesson91.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson91 /tmp/lesson91.s
/tmp/lesson91
echo $?
```

The break emits `jmp .L..N` to the label after the loop's back edge, skipping the
increment. Main returns 42. Tests cover infinite/conditional loops, nested target
restoration, skipped increments, stray breaks, tree and assembly target matching,
prior loop snapshots, and all updated original programs.

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
