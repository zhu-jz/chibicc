"""Package the compiler using only the Python standard library.

Based on chibicc build lesson 5d15431df1abab3a5cf596fabe0a77c030a10791.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import argparse
from pathlib import Path
import shutil
import tempfile
import zipapp


SOURCE_FILES = ("main.py", "common.py", "tokenizer.py", "preprocess.py", "parse.py",
                "type.py", "constexpr.py", "codegen.py", "unicode.py", "hashmap.py", "LICENSE")


def build(output):
    source_directory = Path(__file__).resolve().parent
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    for header in sorted((source_directory / "include").glob("*.h")):
        target = output.parent / "include" / header.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if header.resolve() != target.resolve():
            shutil.copyfile(header, target)
    with tempfile.TemporaryDirectory(prefix="chibicc-package-") as directory:
        stage = Path(directory)
        for name in SOURCE_FILES:
            shutil.copyfile(source_directory / name, stage / name)
        (stage / "__main__.py").write_text(
            "from main import main\nraise SystemExit(main())\n", encoding="utf-8")
        zipapp.create_archive(stage, target=output, interpreter="/usr/bin/env python3")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build a standalone Python compiler archive")
    parser.add_argument("-o", type=Path,
                        default=Path(__file__).resolve().parent / "build" / "chibicc.pyz")
    print(build(parser.parse_args().o))
