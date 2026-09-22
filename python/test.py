"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


COMPILER = Path(__file__).with_name("main.py")


def compile_expression(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


class ExpressionCompilerTests(unittest.TestCase):
    def test_assembly_and_exit_status(self):
        # Keep the first lesson's cases and the original commit's 5+20-4.
        # Expected instruction sequences are explicit: no expression evaluator.
        cases = [
            ("0", "  mov $0, %rax\n", 0),
            ("42", "  mov $42, %rax\n", 42),
            ("255", "  mov $255, %rax\n", 255),
            ("256", "  mov $256, %rax\n", 0),
            ("-1", "  mov $-1, %rax\n", 255),
            (" +0042 ", "  mov $42, %rax\n", 42),
            ("-2147483648", "  mov $-2147483648, %rax\n", 0),
            ("2147483647", "  mov $2147483647, %rax\n", 255),
            ("5+20-4", "  mov $5, %rax\n  add $20, %rax\n  sub $4, %rax\n", 21),
            ("10-3-2", "  mov $10, %rax\n  sub $3, %rax\n  sub $2, %rax\n", 5),
            ("0-1", "  mov $0, %rax\n  sub $1, %rax\n", 255),
            ("255+2", "  mov $255, %rax\n  add $2, %rax\n", 1),
            ("1+-2", "  mov $1, %rax\n  add $-2, %rax\n", 255),
            ("1--2", "  mov $1, %rax\n  sub $-2, %rax\n", 3),
            ("5+ 20-4", "  mov $5, %rax\n  add $20, %rax\n  sub $4, %rax\n", 21),
            ("1+2147483647", "  mov $1, %rax\n  add $2147483647, %rax\n", 0),
            ("0- -2147483648", "  mov $0, %rax\n  sub $-2147483648, %rax\n", 0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            for source, instructions, expected_status in cases:
                with self.subTest(source=source):
                    result = compile_expression(source)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(
                        result.stdout,
                        f"  .globl main\nmain:\n{instructions}  ret\n",
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
                 ("1_000",), ("2147483648",), ("-2147483649",),
                 ("1+",), ("1-",), ("1+abc",), ("1+2junk",),
                 ("1*2",), ("1/2",), ("(1)",), ("1 2",), ("1 +2",),
                 ("1+2147483648",), ("1-2147483649",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = compile_expression(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
