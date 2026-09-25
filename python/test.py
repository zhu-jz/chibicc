"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codegen import CodeGenerator
from common import Function, Node, Obj, Token
from parse import parse
from tokenizer import tokenize


COMPILER = Path(__file__).with_name("main.py")
PROLOGUE = "  .globl main\nmain:\n  push %rbp\n  mov %rsp, %rbp\n"
EPILOGUE = "  mov %rbp, %rsp\n  pop %rbp\n  ret\n"


def compile_program(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


class ExpressionCompilerTests(unittest.TestCase):
    def test_local_objects_and_stack_layout(self):
        program = parse(tokenize("foo=3; bar=5; foo+bar;"))
        self.assertEqual([var.name for var in program.locals], ["bar", "foo"])
        bar, foo = program.locals
        self.assertIs(program.body[0].lhs.lhs.var, foo)
        self.assertIs(program.body[2].lhs.lhs.var, foo)
        self.assertIs(program.body[1].lhs.lhs.var, bar)
        self.assertIs(program.body[2].lhs.rhs.var, bar)
        CodeGenerator().generate(program)
        self.assertEqual((bar.offset, foo.offset, program.stack_size), (-8, -16, 16))
        # A second parse must have its own local-variable objects.
        another = parse(tokenize("foo=1; foo;"))
        self.assertEqual(len(another.locals), 1)
        self.assertIsNot(another.locals[0], foo)
        for source, expected_offsets, expected_size in [
            ("1;", [], 0),
            ("x=1; x=x+1;", [-8], 16),
            ("a=1; b=2; c=3;", [-8, -16, -24], 32),
            ("a=1; b=2; c=3; d=4;", [-8, -16, -24, -32], 32),
        ]:
            with self.subTest(source=source):
                program = parse(tokenize(source))
                assembly = CodeGenerator().generate(program)
                self.assertEqual([var.offset for var in program.locals], expected_offsets)
                self.assertEqual(program.stack_size, expected_size)
                self.assertIn(f"  sub ${expected_size}, %rsp\n", assembly)

    def test_statement_list(self):
        statements = parse(tokenize("1; 2+3;"))
        self.assertEqual(statements.body, [
            Node("EXPR_STMT", lhs=Node("NUM", value=1)),
            Node("EXPR_STMT", lhs=Node("+", Node("NUM", value=2), Node("NUM", value=3))),
        ])
        generator = CodeGenerator()
        generator.generate(statements)
        self.assertEqual(generator.depth, 0)

    def test_empty_program(self):
        # Upstream accepts zero statements but emits no return value.
        # Check the assembly only: the executable's exit status is unspecified.
        for source in ["", " \t\n"]:
            with self.subTest(source=source):
                self.assertEqual(parse(tokenize(source)), Function([], []))
                result = compile_program(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout, PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

    def test_tokenization(self):
        self.assertEqual(tokenize("Foo123=_bar;"), [
            Token("IDENT", "Foo123", 0), Token("PUNCT", "=", 6),
            Token("IDENT", "_bar", 7), Token("PUNCT", ";", 11), Token("EOF", "", 12),
        ])
        self.assertEqual(tokenize("a=z;"), [
            Token("IDENT", "a", 0), Token("PUNCT", "=", 1),
            Token("IDENT", "z", 2), Token("PUNCT", ";", 3), Token("EOF", "", 4),
        ])
        self.assertEqual(tokenize("ab"), [
            Token("IDENT", "ab", 0), Token("EOF", "", 2),
        ])
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
            ("a=b=3;", Node("ASSIGN", Node("VAR", var=Obj("a")),
                           Node("ASSIGN", Node("VAR", var=Obj("b")), Node("NUM", value=3)))),
            ("a=5==6;", Node("ASSIGN", Node("VAR", var=Obj("a")), Node("==", five, six))),
            ('5+6*7;', Node("+", five, Node("*", six, seven))),
            ('(5+6)*7;', Node("*", Node("+", five, six), seven)),
            ('5-6-7;', Node("-", Node("-", five, six), seven)),
            ('5/6/7;', Node("/", Node("/", five, six), seven)),
            ('-5*6;', Node("*", Node("NEG", lhs=five), six)),
            ('-(5+6);', Node("NEG", lhs=Node("+", five, six))),
            ('--5;', Node("NEG", lhs=Node("NEG", lhs=five))),
            ('+-5;', Node("NEG", lhs=five)),
            ('5+6*7==47;', Node("==", Node("+", five, Node("*", six, seven)),
                                Node("NUM", value=47))),
            ('5>6;', Node("<", six, five)),
            ('5>=6;', Node("<=", six, five)),
            ('5<6==1;', Node("==", Node("<", five, six), Node("NUM", value=1))),
            ('5==6<7;', Node("==", five, Node("<", six, seven))),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                tokens = tokenize(source)
                statements = parse(tokens)
                self.assertEqual(statements.body, [Node("EXPR_STMT", lhs=expected)])
                generator = CodeGenerator()
                generator.generate(statements)
                self.assertEqual(generator.depth, 0)

    def test_exact_assembly(self):
        cases = [
            ("a=3; a;", "  lea -8(%rbp), %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  mov %rax, (%rdi)\n  lea -8(%rbp), %rax\n  mov (%rax), %rax\n"),
            ("z=5;", "  lea -8(%rbp), %rax\n  push %rax\n  mov $5, %rax\n"
             "  pop %rdi\n  mov %rax, (%rdi)\n"),
            ("1; 2; 3;", "  mov $1, %rax\n  mov $2, %rax\n  mov $3, %rax\n"),
            ('42;', "  mov $42, %rax\n"),
            ('5+6*7;', "  mov $7, %rax\n  push %rax\n  mov $6, %rax\n"
             "  pop %rdi\n  imul %rdi, %rax\n  push %rax\n  mov $5, %rax\n"
             "  pop %rdi\n  add %rdi, %rax\n"),
            ('(3+5)/2;', "  mov $2, %rax\n  push %rax\n  mov $5, %rax\n"
             "  push %rax\n  mov $3, %rax\n  pop %rdi\n  add %rdi, %rax\n"
             "  pop %rdi\n  cqo\n  idiv %rdi\n"),
            ('10-3;', "  mov $3, %rax\n  push %rax\n  mov $10, %rax\n"
             "  pop %rdi\n  sub %rdi, %rax\n"),
            ('-10;', "  mov $10, %rax\n  neg %rax\n"),
            ('+10;', "  mov $10, %rax\n"),
            ('- - +10;', "  mov $10, %rax\n  neg %rax\n  neg %rax\n"),
            ('2*-(3+4);', "  mov $4, %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  add %rdi, %rax\n  neg %rax\n  push %rax\n"
             "  mov $2, %rax\n  pop %rdi\n  imul %rdi, %rax\n"),
            ('1==2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  sete %al\n  movzb %al, %rax\n"),
            ('1!=2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setne %al\n  movzb %al, %rax\n"),
            ('1<2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setl %al\n  movzb %al, %rax\n"),
            ('1<=2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setle %al\n  movzb %al, %rax\n"),
            ('1>2;', "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setl %al\n  movzb %al, %rax\n"),
            ('1>=2;', "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %rdi, %rax\n  setle %al\n  movzb %al, %rax\n"),
        ]
        for source, instructions in cases:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                stack_size = 16 if source in ("a=3; a;", "z=5;") else 0
                self.assertEqual(result.stdout, PROLOGUE + f"  sub ${stack_size}, %rsp\n" + instructions + EPILOGUE)

    def test_executable_exit_status(self):
        # All original test cases through this commit, previous valid cases, and precedence,
        # grouping, operand-order, and signed-division checks. No Python eval.
        cases = [
            ("foo=3; foo;", 3), ("foo123=3; bar=5; foo123+bar;", 8),
            ("foo=3; foo123=7; foo+foo123;", 10),
            ("Foo=3; foo=7; Foo+foo;", 10),
            ("_=2; _value1=5; _+_value1;", 7),
            ("total=left=right=4; total+left+right;", 12),
            ("count=3; count=count+4; count;", 7),
            ("alpha=1; beta=2; gamma=3; alpha+beta+gamma;", 6),
            ("".join(f"var{i}={i};" for i in range(30))
             + "+".join(f"var{i}" for i in range(30)) + ";", 179),
            ("a=3; a;", 3), ("a=3; z=5; a+z;", 8), ("a=b=3; a+b;", 6),
            ("a=1; a=a+2; a;", 3), ("a=4; b=7; a=9; b;", 7),
            ("a=5==5; a;", 1), ("a=3; (a=7)+2;", 9),
            ("a=-(3+4); b=2; a/b;", 253), ("(a)=6; a;", 6),
            ("a=65536*65536; a/65536/65536;", 1),
            ("a=2; z=8; (a+z)*(z-a); a+z;", 10),
            ("".join(f"{chr(97+i)}={i+1};" for i in range(26))
             + "+".join(chr(97+i) for i in range(26)) + ";", 95),
            ("1; 2; 3;", 3),
            ("42; 0;", 0),
            ("1+2; 3*(4+5); (10-3)/2;", 3),
            ("5<6; -7;", 249),
            ("10;\n 20+22;\n", 42),
            ('0;', 0), ('42;', 42), ('5+20-4;', 21), (' 12 + 34 - 5 ;', 41),
            ('5+6*7;', 47), ('5*(9-6);', 15), ('(3+5)/2;', 4),
            ('255;', 255), ('256;', 0), (' 0042 ;', 42), ('2147483647;', 255),
            ('10-3-2;', 5), ('0-1;', 255), ('255+2;', 1), ('5+ 20-4;', 21),
            ('5 +20-4;', 21), ('\t12\n+\r34\x0b-\x0c5 ;', 41),
            ('1\u2003+\u20032;', 3), ('1+2147483647;', 0), ('0-2147483647-1;', 0),
            ('(5+6)*7;', 77), ('20/3;', 6), ('20/2/2;', 5), ('20/(2/2);', 20),
            ('24/3*2;', 16), ('24/(3*2);', 4), ('20-3*4+8/2;', 12),
            ('((2+3)*(4+(8/2)));', 40), ('((42));', 42),
            ('(0-7)/2;', 253), ('7/(0-2);', 253), ('(0-7)/(0-2);', 3),
            ('(0-3)*4;', 244), ('100/(2+3*(4-2));', 12),
            ('65536*65536/65536/65536;', 1),
            ('-10+20;', 10), ('- -10;', 10), ('- - +10;', 10),
            ('-1;', 255), ('+42;', 42), ('1+-2;', 255),
            ('1--2;', 3), ('1++2;', 3), ('1 + +2;', 3),
            ('-(3+4)*2;', 242), ('2*-(3+4);', 242),
            ('-20/3;', 250), ('20/-3;', 250), ('-20/-3;', 6),
            ('3*-4+15;', 3), ('-(-(-5));', 251),
            ('-2147483647-1;', 0),
            ('0==1;', 0), ('42==42;', 1), ('0!=1;', 1), ('42!=42;', 0),
            ('0<1;', 1), ('1<1;', 0), ('2<1;', 0),
            ('0<=1;', 1), ('1<=1;', 1), ('2<=1;', 0),
            ('1>0;', 1), ('1>1;', 0), ('1>2;', 0),
            ('1>=0;', 1), ('1>=1;', 1), ('1>=2;', 0),
            ('-1<0;', 1), ('0>-1;', 1), ('-2<=-1;', 1),
            ('-1>=0;', 0), ('2147483647+1>0;', 1),
            ('5+6*7==47;', 1), ('5+6*7!=47;', 0),
            ('5==2+3;', 1), ('3<4==1;', 1), ('3==4<5;', 0),
            ('1<2<3;', 1), ('3>2>0;', 1),
            ('(3>2)+4;', 5), ('(5>=5)*7;', 7),
            ('1==1==1;', 1), ('2==2==2;', 0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            for source, expected_status in cases:
                with self.subTest(source=source):
                    result = compile_program(source)
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
        cases = [(), ("1", "2"), ("abc",), ("42abc",),
                 ("1_000",), ("2147483648",), ("-2147483649",),
                 ("1+",), ("1-",), ("1+abc",), ("1+2junk",), ("1 2",),
                 ("1+2147483648",), ("1-2147483649",),
                 ("1 + ",), ("１２",), ("()",), ("(1",), ("1)",),
                 ("2(3)",), ("1**2",), ("1//2",), ("1/",), ("1%2",),
                 ("+",), ("-",), ("--",), ("1*-",),
                 ("1=1",), ("1!2",), ("1<",), ("1>=",),
                 ("1===1",), ("1<>2",), ("1&&2",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                result = compile_program(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_error_messages(self):
        cases = [
            ("42", "42\n  ^ expected ';'\n"),
            ("1; 2", "1; 2\n    ^ expected ';'\n"),
            (";", ";\n^ expected an expression\n"),
            ("1;;", "1;;\n  ^ expected an expression\n"),
            ("1; 2+;", "1; 2+;\n     ^ expected an expression\n"),
            ("1; (2;", "1; (2;\n     ^ expected ')'\n"),
            ("1@2", "1@2\n ^ expected ';'\n"),
            ("1+foo", "1+foo\n     ^ expected ';'\n"),
            ("1+", "1+\n  ^ expected an expression\n"),
            (" 12 +   ", " 12 +   \n        ^ expected an expression\n"),
            ("18 11", "18 11\n   ^ expected ';'\n"),
            ("--", "--\n  ^ expected an expression\n"),
            ("1 + +", "1 + +\n     ^ expected an expression\n"),
            (" 12 + foo", " 12 + foo\n         ^ expected ';'\n"),
            ("1+2147483648", "1+2147483648\n  ^ integer must fit in a signed 32-bit immediate\n"),
            ("1\u2003+@", "1\u2003+@\n   ^ expected an expression\n"),
            ("(1+2", "(1+2\n    ^ expected ')'\n"),
            ("1)", "1)\n ^ expected ';'\n"),
            ("()", "()\n ^ expected an expression\n"),
            ("1/", "1/\n  ^ expected an expression\n"),
            ("(1 2)", "(1 2)\n   ^ expected ')'\n"),
            ("1=1;", "not an lvalue\n"),
            ("(a+1)=3;", "not an lvalue\n"),
            ("-a=3;", "not an lvalue\n"),
            ("a=;", "a=;\n  ^ expected an expression\n"),
            ("é=3;", "é=3;\n^ invalid token\n"),
            ("12abc=3;", "12abc=3;\n  ^ expected ';'\n"),
            ("1<", "1<\n  ^ expected an expression\n"),
            ("1>=", "1>=\n   ^ expected an expression\n"),
            ("1===1", "1===1\n   ^ expected an expression\n"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected)

    def test_argument_error_has_no_source_location(self):
        for arguments in [(), ("1", "2")]:
            with self.subTest(arguments=arguments):
                result = compile_program(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, f"{COMPILER}: invalid number of arguments\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
