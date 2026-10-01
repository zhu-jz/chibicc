# Lesson 192: Add the GNU __FUNCTION__ identifier

Original chibicc commit: [`82ba010c764d3dc4d0f72a9ee5a6d6f72780e75f`](https://github.com/rui314/chibicc/commit/82ba010c764d3dc4d0f72a9ee5a6d6f72780e75f).
Earlier explanations are available in Git history.

Every function definition now also binds `__FUNCTION__` to a static character
array containing the current function name. It is GNU's alternate name for the
same information supplied by `__func__`, and is introduced by the parser rather
than by macro expansion.

This original commit creates a separate string object for each binding, even
when neither is used. Their bytes and sizes match but their addresses differ
in this compiler. Python preserves both objects and their function-scope
bindings. Anonymous label numbers shift once more; tests inspect strings and
select functions by name rather than assuming every global object is a function.

```sh
printf 'int main(void){return sizeof(__FUNCTION__);}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 5 for main plus its terminating zero
```

Assembly emits two static strings with the bytes of main and a zero. sizeof
becomes a constant, so the function loads 5 into `%rax` and returns through
its frame cleanup. A character reference instead loads from the selected
string's address. Tests cover size, returning the string, distinct addresses,
shadowing and rejection outside a function; the original function fixture runs
unchanged. Both complete source and packaged compiler suites are checked.

This completes the requested batch of fifty consecutive lessons, 143–192.
The README describes this current lesson; earlier explanations remain in each
Python Git commit, which records its corresponding full original commit hash.

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
