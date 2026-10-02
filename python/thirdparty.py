"""Run the pinned third-party application workflows with the Python compiler.

Based on chibicc commit fb4937024db2ee06fd60ea3bb2cfc6c898646a7d.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import argparse
import os
from pathlib import Path
import shlex
import subprocess

from build import build


PROJECTS = {
    "git": ("https://github.com/git/git.git", "54e85e7af1ac9e9a92888060d6811ae767fea1bc"),
    "libpng": ("https://github.com/rui314/libpng.git", "dbe3e0c43e549a1602286144d94b0666549b18e6"),
    "sqlite": ("https://github.com/sqlite/sqlite.git", "86f477edaa17767b39c7bae5b67cac8580f7a8c1"),
    "tinycc": ("https://github.com/TinyCC/tinycc.git", "df67d8617b7d1d03a480a28f9f901848ffbfb7ec"),
}


def patch_libtool(directory):
    path = directory / "libtool"
    lines = path.read_text().splitlines(keepends=True)
    for index, line in enumerate(lines):
        if line.startswith("wl="):
            lines[index] = "wl=-Wl,\n"
        elif line.startswith("pic_flag="):
            lines[index] = "pic_flag=-fPIC\n"
    path.write_text("".join(lines))


def run_project(project, work_directory, compiler, jobs=1, dry_run=False):
    repository, revision = PROJECTS[project]
    checkout = Path(work_directory).resolve() / (project + "-" + revision[:12])
    compiler = Path(compiler).resolve()

    def run(command, directory=checkout, environment=None):
        print(f"[{directory}] {shlex.join(command)}", flush=True)
        if not dry_run:
            subprocess.run(command, cwd=directory, env=environment, check=True)

    if dry_run or not (checkout / ".git").exists():
        if not dry_run:
            checkout.mkdir(parents=True, exist_ok=False)
        run(["git", "init"])
        run(["git", "remote", "add", "origin", repository])
        run(["git", "fetch", "--depth=1", "origin", revision])
        run(["git", "checkout", "--detach", "FETCH_HEAD"])
    elif not dry_run:
        actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
        if actual != revision:
            raise RuntimeError(f"{checkout}: checkout does not match pinned revision {revision}")

    make = ["make", f"-j{jobs}"]
    cc = "CC=" + shlex.quote(str(compiler))
    if project == "git":
        run(make + ["clean"])
        run(make + ["V=1", cc, "test"])
        return
    if project == "tinycc":
        run(["./configure", "--cc=" + str(compiler)])
        run(make + ["clean"])
        run(make)
        run(make + ["CC=cc", "test"])
        return
    environment = dict(os.environ, CC=shlex.quote(str(compiler)))
    if project == "sqlite":
        environment["CFLAGS"] = "-D_GNU_SOURCE"
    print("configure environment: CC=" + environment["CC"] +
          (" CFLAGS=-D_GNU_SOURCE" if project == "sqlite" else ""), flush=True)
    run(["./configure"], environment=environment)
    if dry_run:
        print("patch libtool: wl=-Wl, pic_flag=-fPIC", flush=True)
    else:
        patch_libtool(checkout)
    run(make + ["clean"])
    run(make)
    run(make + ["test"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", choices=PROJECTS)
    parser.add_argument("--work-dir", type=Path, default=Path(__file__).parent / "thirdparty")
    parser.add_argument("--compiler", type=Path)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args()
    if options.jobs < 1:
        parser.error("--jobs must be positive")
    try:
        compiler = options.compiler or Path(__file__).parent / "build" / "chibicc.pyz"
        if options.compiler is None and not options.dry_run:
            compiler = build(compiler)
        run_project(options.project, options.work_dir, compiler, options.jobs, options.dry_run)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
