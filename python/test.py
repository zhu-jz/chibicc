"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


COMPILER = Path(__file__).with_name("main.py")


def compile_integer(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


class IntegerCompilerTests(unittest.TestCase):
    def test_assembly_and_exit_status(self):
        # The original tests are 0 and 42. Also check signs and exit-status
        # truncation, and ensure both signed 32-bit boundaries assemble.
        cases = [
            ("0", 0, 0),
            ("42", 42, 42),
            ("255", 255, 255),
            ("256", 256, 0),
            ("-1", -1, 255),
            (" +0042 ", 42, 42),
            ("-2147483648", -2147483648, 0),
            ("2147483647", 2147483647, 255),
        ]
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            for source, value, expected_status in cases:
                with self.subTest(source=source):
                    result = compile_integer(source)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(
                        result.stdout,
                        f"  .globl main\nmain:\n  mov ${value}, %rax\n  ret\n",
                    )
                    assembly.write_text(result.stdout)
                    linked = subprocess.run(
                        ["gcc", "-static", "-Wl,-z,noexecstack", "-o",
                         str(executable), str(assembly)],
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(linked.returncode, 0, linked.stderr)
                    executed = subprocess.run([str(executable)])
                    self.assertEqual(executed.returncode, expected_status)

    def test_invalid_arguments(self):
        cases = [(), ("1", "2"), ("",), ("abc",), ("42abc",),
                 ("1+2",), ("1_000",), ("2147483648",), ("-2147483649",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = compile_integer(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
