"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from main import Token, tokenize


COMPILER = Path(__file__).with_name("main.py")


def compile_expression(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


class ExpressionCompilerTests(unittest.TestCase):
    def test_tokenization(self):
        expected = [
            Token("NUM", "12", 12), Token("PUNCT", "+"),
            Token("NUM", "34", 34), Token("PUNCT", "-"),
            Token("NUM", "5", 5), Token("EOF", ""),
        ]
        self.assertEqual(tokenize(" 12 + 34 - 5 "), expected)
        self.assertEqual(tokenize("12+34-5"), expected)
        self.assertEqual(tokenize(" \t\n"), [Token("EOF", "")])
        self.assertEqual(tokenize("-001"), [
            Token("PUNCT", "-"), Token("NUM", "001", 1), Token("EOF", ""),
        ])

    def test_assembly_and_exit_status(self):
        # Include all four original tests through this commit.
        # Expected instruction sequences are explicit: no expression evaluator.
        cases = [
            ("0", "  mov $0, %rax\n", 0),
            ("42", "  mov $42, %rax\n", 42),
            ("255", "  mov $255, %rax\n", 255),
            ("256", "  mov $256, %rax\n", 0),
            (" 0042 ", "  mov $42, %rax\n", 42),
            ("2147483647", "  mov $2147483647, %rax\n", 255),
            ("5+20-4", "  mov $5, %rax\n  add $20, %rax\n  sub $4, %rax\n", 21),
            ("10-3-2", "  mov $10, %rax\n  sub $3, %rax\n  sub $2, %rax\n", 5),
            ("0-1", "  mov $0, %rax\n  sub $1, %rax\n", 255),
            ("255+2", "  mov $255, %rax\n  add $2, %rax\n", 1),
            ("5+ 20-4", "  mov $5, %rax\n  add $20, %rax\n  sub $4, %rax\n", 21),
            ("5 +20-4", "  mov $5, %rax\n  add $20, %rax\n  sub $4, %rax\n", 21),
            (" 12 + 34 - 5 ", "  mov $12, %rax\n  add $34, %rax\n  sub $5, %rax\n", 41),
            ("\t12\n+\r34\v-\f5 ", "  mov $12, %rax\n  add $34, %rax\n  sub $5, %rax\n", 41),
            ("1\u2003+\u20032", "  mov $1, %rax\n  add $2, %rax\n", 3),
            ("1+2147483647", "  mov $1, %rax\n  add $2147483647, %rax\n", 0),
            ("0-2147483647-1", "  mov $0, %rax\n  sub $2147483647, %rax\n  sub $1, %rax\n", 0),
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
                 ("1*2",), ("1/2",), ("(1)",), ("1 2",),
                 ("1+2147483648",), ("1-2147483649",), (" \t\n",),
                 ("-1",), ("+42",), ("1+-2",), ("1--2",), ("1++2",),
                 ("1 + ",), ("１２",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = compile_expression(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_error_messages(self):
        cases = [("1@2", "invalid token"), ("1+", "expected a number"),
                 ("", "expected a number"), ("1 2", "expected '-'"),
                 ("-1", "expected a number")]
        for source, message in cases:
            with self.subTest(source=source):
                result = compile_expression(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, message + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
