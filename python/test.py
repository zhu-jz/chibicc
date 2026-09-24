"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codegen import CodeGenerator
from common import Node, Token
from parse import parse
from tokenizer import tokenize


COMPILER = Path(__file__).with_name("main.py")


def compile_expression(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


class ExpressionCompilerTests(unittest.TestCase):
    def test_tokenization(self):
        self.assertEqual(tokenize(" 1<=2 != 3>=4 == 5 < 6 > 7 "), [
            Token("NUM", "1", 1, 1), Token("PUNCT", "<=", 2),
            Token("NUM", "2", 4, 2), Token("PUNCT", "!=", 6),
            Token("NUM", "3", 9, 3), Token("PUNCT", ">=", 10),
            Token("NUM", "4", 12, 4), Token("PUNCT", "==", 14),
            Token("NUM", "5", 17, 5), Token("PUNCT", "<", 19),
            Token("NUM", "6", 21, 6), Token("PUNCT", ">", 23),
            Token("NUM", "7", 25, 7), Token("EOF", "", 27),
        ])
        self.assertEqual(tokenize(" 12 * (3 / 2) "), [
            Token("NUM", "12", 1, 12), Token("PUNCT", "*", 4),
            Token("PUNCT", "(", 6), Token("NUM", "3", 7, 3),
            Token("PUNCT", "/", 9), Token("NUM", "2", 11, 2),
            Token("PUNCT", ")", 12), Token("EOF", "", 14),
        ])
        self.assertEqual(tokenize(" \t\n"), [Token("EOF", "", 3)])
        self.assertEqual(tokenize("-001"), [
            Token("PUNCT", "-", 0), Token("NUM", "001", 1, 1), Token("EOF", "", 4),
        ])
        # Like C ispunct, tokenization recognizes even unsupported punctuation.
        self.assertEqual(tokenize("@"), [Token("PUNCT", "@", 0), Token("EOF", "", 1)])

    def test_tree_structure(self):
        five = Node("NUM", value=5)
        six = Node("NUM", value=6)
        seven = Node("NUM", value=7)
        cases = [
            ("5+6*7", Node("+", five, Node("*", six, seven))),
            ("(5+6)*7", Node("*", Node("+", five, six), seven)),
            ("5-6-7", Node("-", Node("-", five, six), seven)),
            ("5/6/7", Node("/", Node("/", five, six), seven)),
            ("-5*6", Node("*", Node("NEG", lhs=five), six)),
            ("-(5+6)", Node("NEG", lhs=Node("+", five, six))),
            ("--5", Node("NEG", lhs=Node("NEG", lhs=five))),
            ("+-5", Node("NEG", lhs=five)),
            ("5+6*7==47", Node("==", Node("+", five, Node("*", six, seven)),
                                Node("NUM", value=47))),
            ("5>6", Node("<", six, five)),
            ("5>=6", Node("<=", six, five)),
            ("5<6==1", Node("==", Node("<", five, six), Node("NUM", value=1))),
            ("5==6<7", Node("==", five, Node("<", six, seven))),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                tokens = tokenize(source)
                node = parse(tokens)
                self.assertEqual(node, expected)
                generator = CodeGenerator()
                generator.generate(node)
                self.assertEqual(generator.depth, 0)

    def test_exact_assembly(self):
        cases = [
            ("42", "  mov $42, %rax\n"),
            ("5+6*7", "  mov $7, %rax\n  push %rax\n  mov $6, %rax\n"
             "  pop %rdi\n  imul %rdi, %rax\n  push %rax\n  mov $5, %rax\n"
             "  pop %rdi\n  add %rdi, %rax\n"),
            ("(3+5)/2", "  mov $2, %rax\n  push %rax\n  mov $5, %rax\n"
             "  push %rax\n  mov $3, %rax\n  pop %rdi\n  add %rdi, %rax\n"
             "  pop %rdi\n  cqo\n  idiv %rdi\n"),
            ("10-3", "  mov $3, %rax\n  push %rax\n  mov $10, %rax\n"
             "  pop %rdi\n  sub %rdi, %rax\n"),
            ("-10", "  mov $10, %rax\n  neg %rax\n"),
            ("+10", "  mov $10, %rax\n"),
            ("- - +10", "  mov $10, %rax\n  neg %rax\n  neg %rax\n"),
            ("2*-(3+4)", "  mov $4, %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  add %rdi, %rax\n  neg %rax\n  push %rax\n"
             "  mov $2, %rax\n  pop %rdi\n  imul %rdi, %rax\n"),
            ("1==2", "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  sete %al\n  movzb %al, %rax\n"),
            ("1!=2", "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setne %al\n  movzb %al, %rax\n"),
            ("1<2", "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setl %al\n  movzb %al, %rax\n"),
            ("1<=2", "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setle %al\n  movzb %al, %rax\n"),
            ("1>2", "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setl %al\n  movzb %al, %rax\n"),
            ("1>=2", "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setle %al\n  movzb %al, %rax\n"),
        ]
        for source, instructions in cases:
            with self.subTest(source=source):
                result = compile_expression(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout, f"  .globl main\nmain:\n{instructions}  ret\n")

    def test_executable_exit_status(self):
        # All 26 original tests, previous valid cases, and precedence,
        # grouping, operand-order, and signed-division checks. No Python eval.
        cases = [
            ("0", 0), ("42", 42), ("5+20-4", 21), (" 12 + 34 - 5 ", 41),
            ("5+6*7", 47), ("5*(9-6)", 15), ("(3+5)/2", 4),
            ("255", 255), ("256", 0), (" 0042 ", 42), ("2147483647", 255),
            ("10-3-2", 5), ("0-1", 255), ("255+2", 1), ("5+ 20-4", 21),
            ("5 +20-4", 21), ("\t12\n+\r34\v-\f5 ", 41),
            ("1\u2003+\u20032", 3), ("1+2147483647", 0), ("0-2147483647-1", 0),
            ("(5+6)*7", 77), ("20/3", 6), ("20/2/2", 5), ("20/(2/2)", 20),
            ("24/3*2", 16), ("24/(3*2)", 4), ("20-3*4+8/2", 12),
            ("((2+3)*(4+(8/2)))", 40), ("((42))", 42),
            ("(0-7)/2", 253), ("7/(0-2)", 253), ("(0-7)/(0-2)", 3),
            ("(0-3)*4", 244), ("100/(2+3*(4-2))", 12),
            ("65536*65536/65536/65536", 1),
            ("-10+20", 10), ("- -10", 10), ("- - +10", 10),
            ("-1", 255), ("+42", 42), ("1+-2", 255),
            ("1--2", 3), ("1++2", 3), ("1 + +2", 3),
            ("-(3+4)*2", 242), ("2*-(3+4)", 242),
            ("-20/3", 250), ("20/-3", 250), ("-20/-3", 6),
            ("3*-4+15", 3), ("-(-(-5))", 251),
            ("-2147483647-1", 0),
            ("0==1", 0), ("42==42", 1), ("0!=1", 1), ("42!=42", 0),
            ("0<1", 1), ("1<1", 0), ("2<1", 0),
            ("0<=1", 1), ("1<=1", 1), ("2<=1", 0),
            ("1>0", 1), ("1>1", 0), ("1>2", 0),
            ("1>=0", 1), ("1>=1", 1), ("1>=2", 0),
            ("-1<0", 1), ("0>-1", 1), ("-2<=-1", 1),
            ("-1>=0", 0), ("2147483647+1>0", 1),
            ("5+6*7==47", 1), ("5+6*7!=47", 0),
            ("5==2+3", 1), ("3<4==1", 1), ("3==4<5", 0),
            ("1<2<3", 1), ("3>2>0", 1),
            ("(3>2)+4", 5), ("(5>=5)*7", 7),
            ("1==1==1", 1), ("2==2==2", 0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            for source, expected_status in cases:
                with self.subTest(source=source):
                    result = compile_expression(source)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, "")
                    assembly.write_text(result.stdout)
                    linked = subprocess.run(
                        ["gcc", "-static", "-Wl,-z,noexecstack", "-o",
                         str(executable), str(assembly)],
                        capture_output=True, text=True,
                    )
                    self.assertEqual(linked.returncode, 0, linked.stderr)
                    executed = subprocess.run([str(executable)])
                    self.assertEqual(executed.returncode, expected_status)

    def test_invalid_arguments(self):
        cases = [(), ("1", "2"), ("",), ("abc",), ("42abc",),
                 ("1_000",), ("2147483648",), ("-2147483649",),
                 ("1+",), ("1-",), ("1+abc",), ("1+2junk",), ("1 2",),
                 ("1+2147483648",), ("1-2147483649",), (" \t\n",),
                 ("1 + ",), ("１２",), ("()",), ("(1",), ("1)",),
                 ("2(3)",), ("1**2",), ("1//2",), ("1/",), ("1%2",),
                 ("+",), ("-",), ("--",), ("1*-"),
                 ("1=1",), ("1!2",), ("1<",), ("1>=",),
                 ("1===1",), ("1<>2",), ("1&&2",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = compile_expression(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_error_messages(self):
        cases = [
            ("1@2", "1@2\n ^ extra token\n"),
            ("1+foo", "1+foo\n  ^ invalid token\n"),
            ("1+", "1+\n  ^ expected an expression\n"),
            (" 12 +   ", " 12 +   \n        ^ expected an expression\n"),
            ("", "\n^ expected an expression\n"),
            ("   ", "   \n   ^ expected an expression\n"),
            ("18 11", "18 11\n   ^ extra token\n"),
            ("--", "--\n  ^ expected an expression\n"),
            ("1 + +", "1 + +\n     ^ expected an expression\n"),
            (" 12 + foo", " 12 + foo\n      ^ invalid token\n"),
            ("1+2147483648", "1+2147483648\n  ^ integer must fit in a signed 32-bit immediate\n"),
            ("1\u2003+@", "1\u2003+@\n   ^ expected an expression\n"),
            ("(1+2", "(1+2\n    ^ expected ')'\n"),
            ("1)", "1)\n ^ extra token\n"),
            ("()", "()\n ^ expected an expression\n"),
            ("1/", "1/\n  ^ expected an expression\n"),
            ("(1 2)", "(1 2)\n   ^ expected ')'\n"),
            ("1=1", "1=1\n ^ extra token\n"),
            ("1<", "1<\n  ^ expected an expression\n"),
            ("1>=", "1>=\n   ^ expected an expression\n"),
            ("1===1", "1===1\n   ^ expected an expression\n"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                result = compile_expression(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected)

    def test_argument_error_has_no_source_location(self):
        for arguments in [(), ("1", "2")]:
            with self.subTest(arguments=arguments):
                result = compile_expression(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, f"{COMPILER}: invalid number of arguments\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
