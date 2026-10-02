# Lesson 306: Add pinned third-party application test runners

Original chibicc commit: [`fb4937024db2ee06fd60ea3bb2cfc6c898646a7d`](https://github.com/rui314/chibicc/commit/fb4937024db2ee06fd60ea3bb2cfc6c898646a7d).
Earlier explanations are available in Git history.

The original adds optional build/test scripts for Git, libpng, SQLite and TinyCC.
Their exact scripts are preserved under test/thirdparty; thirdparty.py adapts the
workflows to our executable Python compiler archive. It fetches each pinned
revision into an ignored project-and-revision directory, builds with that compiler,
and runs the same application test commands. Use --dry-run to inspect a workflow.

```sh
python3 python/thirdparty.py git --dry-run --jobs 1
printf 'int main(void){return 42;}\n' > /tmp/lesson.c
python3 python/main.py -S -o /tmp/lesson.s /tmp/lesson.c
gcc -o /tmp/lesson /tmp/lesson.s
/tmp/lesson
echo $?  # 42
```

This commit changes development tooling rather than assembly; main still returns
42 in rax. To run a real application workflow, omit --dry-run, for example:
python3 python/thirdparty.py git --jobs 4. It needs Git, Make, network access and
the selected application's build dependencies. Its original pinned versions and
libtool wl/PIC adjustments are retained; TinyCC's final tests use native cc as in C.

Tests check all four dry-run workflows, shell syntax of the preserved scripts,
libtool edits, and a real local Git fetch/build/test using the packaged Python
compiler. The full external application suites are optional and have not been
run by those tests. Python uses HTTPS and shallow pinned fetches rather than SSH
clones, and reuses revision-specific checkouts without hard-resetting edited files.
The runner is a development tool, not part of the compiler archive. MIT attribution
is preserved; downloaded third-party projects retain their own licenses.

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
