# Lesson 44: Block scope

Original chibicc commit: [`ca8b2434c97fc37c14eddcb3a4e831d030ebb041`](https://github.com/rui314/chibicc/commit/ca8b2434c97fc37c14eddcb3a4e831d030ebb041).
Earlier explanations are available in Git history.

## What changed

Name lookup searches a stack of scopes, from the innermost block outward.
Every compound statement enters a scope at `{` and leaves it at `}`. A
function also gives parameters their own enclosing scope. Globals live in the
outermost scope; locals from an earlier function cannot leak into another.

The scopes control visibility, while `function.locals` collects storage for
all variables in that function, even after their names leave scope. Two
variables called `x` are separate objects with separate stack slots. Python
lists replace upstream's linked Scope and VarScope records.

For `int x=2; {int x=3;} return x;`, the final lookup finds the outer `x`, so
the result is 2. In `{x=3;}` without a declaration, lookup finds and changes
the outer object. Statement expressions also use their block's scope.

## Assembly and WSL example

```sh
printf 'int main(){int x=2; {int x=3;} return x;}\n' > /tmp/lesson44.c
python3 python/main.py -o /tmp/lesson44.s /tmp/lesson44.c
cat /tmp/lesson44.s
gcc -static -Wl,-z,noexecstack -o /tmp/lesson44 /tmp/lesson44.s
/tmp/lesson44
echo $?
```

The two initializations store into different offsets from `%rbp`. The final
load reads the outer variable, puts 2 in `%rax`, and returns through the
function epilogue. The executable prints nothing; the shell displays status 2.

Tests cover all three upstream examples, global and parameter shadowing,
statement-expression scopes, forbidden uses after a scope ends, cross-function
leaks, and retaining all local storage objects. Same-scope redeclarations are
still not diagnosed, matching this stage of upstream. Ints remain eight bytes.

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
