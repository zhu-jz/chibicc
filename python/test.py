"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from codegen import CodeGenerator
from common import CompileError, Function, Node, Token
from parse import parse
from tokenizer import tokenize
from type import ty_int


COMPILER = Path(__file__).with_name("main.py")
PROLOGUE = "  .globl main\nmain:\n  push %rbp\n  mov %rsp, %rbp\n"
EPILOGUE = ".L.return:\n  mov %rbp, %rsp\n  pop %rbp\n  ret\n"


def compile_program(*arguments):
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


def parse_body(source):
    """Wrap earlier lesson fixtures in the now-required outer block."""
    return parse(tokenize("{" + source + "}"))


class ExpressionCompilerTests(unittest.TestCase):
    def test_pointer_arithmetic(self):
        for source, expected in [
            ("{int x=3; int y=5; return *(1+&x);}", 5),
            ("{int x=3; int y=5; return &y-&x;}", 1),
            ("{int x=3; int y=5; return &x-&y;}", 255),
            ("{int x=3; return (&x+3)-(&x+1);}", 2),
            ("{int x=3; return (&x-2)-&x;}", 254),
            ("{int x=3; int y=5; int *p=&x; return *(p+1);}", 5),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        expression = parse_body("int x; return &x+1;").body.body[-1].lhs
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.ty.base.kind, "INT")
        self.assertEqual(expression.rhs.kind, "*")
        self.assertEqual(expression.rhs.rhs.value, 8)
        expression = parse_body("int x,y; return &x-&y;").body.body[-1].lhs
        self.assertIs(expression.ty, ty_int)
        self.assertEqual(expression.kind, "/")
        self.assertIs(expression.lhs.ty, ty_int)
        self.assertEqual(expression.rhs.value, 8)
        expression = parse_body("int x; return &x-1+2;").body.body[-1].lhs
        self.assertEqual(expression.lhs.ty.kind, "PTR")
        expression = parse_body("int x; int *p=&x; return p+1;").body.body[-1].lhs
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.rhs.kind, "*")

    def test_address_and_dereference(self):
        for source, expected in [
            ("{ int x=3; return *&x; }", 3),
            ("{ int x=3; int *y=&x; int **z=&y; return **z; }", 3),
            ("{ int x=3; int y=5; return *(&x+1); }", 5),
            ("{ int x=3; int y=5; return *(&y-1); }", 3),
            ("{ int x=3; int *y=&x; *y=5; return x; }", 5),
            ("{ int x=3; int y=5; *(&x+1)=7; return y; }", 7),
            ("{ int x=3; int y=5; *(&y-1)=7; return x; }", 7),
            ("{ int x=1; int *p=&x; int **q=&p; **q=9; return x; }", 9),
            ("{ int x=1; *&x=7; return x; }", 7),
            ("{ int x=3; int *p=&x; return &*p==p; }", 1),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("int *x; 1**x;")
        expression = program.body.body[1].lhs
        self.assertEqual(expression.kind, "*")
        self.assertEqual(expression.rhs.kind, "DEREF")
        self.assertEqual(expression.rhs.tok.text, "*")
        result = compile_program("{int x; return &x;}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -8(%rbp), %rax\n  jmp .L.return\n" + EPILOGUE)
        result = compile_program("{int x; return *&x;}")
        self.assertEqual(result.stdout, PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -8(%rbp), %rax\n  mov (%rax), %rax\n"
                         "  jmp .L.return\n" + EPILOGUE)
        for source, position in [("{return &1;}", 9),
                                 ("{return &(1+2);}", 11)]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, source + "\n" + " " * position
                             + "^ not an lvalue\n")

    def test_representative_tokens(self):
        source = "{return -(1+2)*3>4;}"
        tokens = tokenize(source)
        program = parse(tokens)
        statement = program.body.body[0]
        self.assertIs(program.body.tok, tokens[1])
        self.assertIs(statement.tok, tokens[1])
        comparison = statement.lhs
        self.assertEqual(comparison.kind, "<")
        self.assertEqual(comparison.tok.text, ">")
        multiply = comparison.rhs
        self.assertEqual(multiply.tok.position, source.index("*"))
        self.assertEqual(multiply.lhs.tok.position, source.index("-"))
        self.assertEqual(multiply.lhs.lhs.tok.position, source.index("+"))
        self.assertEqual(multiply.rhs.tok.text, "3")
        for source, position in [("{1=2;}", 1), ("{(1+2)=3;}", 3),
                                 ("{int a; -a=3;}", 8), ("{(2>1)=3;}", 3)]:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, source + "\n" + " " * position
                                 + "^ not an lvalue\n")
        token = Token("PUNCT", "?", 8)
        for generate, node, message in [
            (CodeGenerator().gen_stmt, Node("UNKNOWN", tok=token), "invalid statement"),
            (CodeGenerator().gen_expr, Node("UNKNOWN", Node("NUM"), Node("NUM"),
                                           tok=token), "invalid expression"),
        ]:
            with self.assertRaises(CompileError) as caught:
                generate(node)
            self.assertEqual(caught.exception.position, 8)
            self.assertEqual(str(caught.exception), message)

    def test_while(self):
        for source, expected in [
            ('{int i; i=0; while(i<10) {i=i+1;} return i;}', 10),
            ("{while(0) return 9; return 3;}", 3),
            ("{while(-2) return 7;}", 7),
            ('{int i, sum; i=3; sum=0; while(i) {sum=sum+i; i=i-1;} return sum;}', 6),
            ('{int i, j; i=0; while(i<3) {for(j=0;j<2;j=j+1); i=i+1;} return i+j;}', 5),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("while(1) return 3;")
        node = program.body.body[0]
        self.assertEqual(node.kind, "FOR")
        self.assertIsNone(node.init)
        self.assertIsNone(node.inc)
        expected = CodeGenerator().generate(parse_body("for(;1;) return 3;"))
        self.assertEqual(CodeGenerator().generate(program), expected)
        result = compile_program("{while() ;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected an expression", result.stderr)

    def assert_program_returns(self, source, expected):
        result = compile_program(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            assembly.write_text(result.stdout)
            linked = subprocess.run(
                ["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), str(assembly)],
                capture_output=True, text=True,
            )
            self.assertEqual(linked.returncode, 0, linked.stderr)
            executed = subprocess.run([str(executable)], timeout=5)
            self.assertEqual(executed.returncode, expected)

    def test_for(self):
        cases = [
            ('{int i, j;  i=0; j=0; for(i=0;i<=10;i=i+1) j=i+j; return j; }', 55),
            ("{ for(;;) {return 3;} return 5; }", 3),
            ('{int i;  i=4; for(;i<4;i=i+1) return 9; return i; }', 4),
            ('{int i;  i=0; for(;i<3;) i=i+1; return i; }', 3),
            ('{int i;  i=0; for(;;i=i+1) if(i==4) return i; }', 4),
            ('{int sum, i, j;  sum=0; for(i=0;i<3;i=i+1) for(j=0;j<2;j=j+1) sum=sum+1; return sum; }', 6),
            ('{int i;  for(i=0;i<3;i=i+1); return i; }', 3),
            ('{int format;  format=7; return format; }', 7),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("for(;;) return 3;")
        node = program.body.body[0]
        self.assertEqual(node.init, Node("BLOCK"))
        self.assertIsNone(node.cond)
        self.assertIsNone(node.inc)
        self.assertEqual(CodeGenerator().generate(program) + "\n", PROLOGUE + "  sub $0, %rsp\n"
                         ".L.begin.1:\n  mov $3, %rax\n  jmp .L.return\n"
                         "  jmp .L.begin.1\n.L.end.1:\n" + EPILOGUE)
        for source, position, message in [
            ("{for 1;}", 5, "expected '('"),
            ("{for(1 2;3) ;}", 7, "expected ';'"),
            ("{for(;1 2;) ;}", 8, "expected ';'"),
            ("{for(;;1 2) ;}", 9, "expected ')'"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, source + "\n" + " " * position + "^ " + message + "\n")

    def test_if_tree_and_labels(self):
        program = parse_body("if(1) if(0) return 2; else return 3;")
        outer = program.body.body[0]
        self.assertEqual(outer.kind, "IF")
        self.assertEqual(outer.cond, Node("NUM", value=1))
        self.assertIsNone(outer.els)
        self.assertEqual(outer.then.els, Node("RETURN", lhs=Node("NUM", value=3)))
        assembly = CodeGenerator().generate(program)
        for label in (".L.else.1:", ".L.end.1:", ".L.else.2:", ".L.end.2:"):
            self.assertEqual(assembly.count(label), 1)

    def test_null_statements(self):
        program = parse(tokenize("{ ;;; return 5; }"))
        self.assertEqual(program.body, Node("BLOCK", body=[
            Node("BLOCK"), Node("BLOCK"), Node("BLOCK"),
            Node("RETURN", lhs=Node("NUM", value=5)),
        ]))
        for source in ["{ ;;; return 5; }", "{ {}; return 5;; }", "{ return 5; ;;; }"]:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, PROLOGUE + "  sub $0, %rsp\n"
                                 "  mov $5, %rax\n  jmp .L.return\n" + EPILOGUE)
        # A program containing only null statements does not set a return value.
        result = compile_program("{;;;}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

    def test_nested_block_tree(self):
        program = parse(tokenize("{ {1;} return 2; }"))
        self.assertEqual(program.body, Node("BLOCK", body=[
            Node("BLOCK", body=[Node("EXPR_STMT", lhs=Node("NUM", value=1))]),
            Node("RETURN", lhs=Node("NUM", value=2)),
        ]))
        result = compile_program("{ {1;} return 2; }")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, PROLOGUE + "  sub $0, %rsp\n"
                         "  mov $1, %rax\n  mov $2, %rax\n  jmp .L.return\n" + EPILOGUE)

    def test_block_errors_and_upstream_trailing_tokens(self):
        cases = [
            ("return 1;", "return 1;\n^ expected '{'\n"),
            ("", "\n^ expected '{'\n"),
            ("{", "{\n ^ expected an expression\n"),
            ("{{}", "{{}\n   ^ expected an expression\n"),
            ("{return 1}", "{return 1}\n         ^ expected ';'\n"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected)
        # Upstream tokenizes everything, but parses only the first outer block.
        normal = compile_program("{return 3;}")
        trailing = compile_program("{return 3;} return 9;")
        self.assertEqual(trailing.returncode, 0, trailing.stderr)
        self.assertEqual(trailing.stdout, normal.stdout)

    def test_return_tree(self):
        program = parse_body("return 1+2; 3;")
        self.assertEqual(program.body.body, [
            Node("RETURN", lhs=Node("+", Node("NUM", value=1), Node("NUM", value=2))),
            Node("EXPR_STMT", lhs=Node("NUM", value=3)),
        ])

    def test_local_objects_and_stack_layout(self):
        program = parse_body("int foo=3; int bar=5; return foo+bar;")
        self.assertEqual([var.name for var in program.locals], ["bar", "foo"])
        bar, foo = program.locals
        self.assertIs(program.body.body[0].body[0].lhs.lhs.var, foo)
        self.assertIs(program.body.body[2].lhs.lhs.var, foo)
        self.assertIs(program.body.body[1].body[0].lhs.lhs.var, bar)
        self.assertIs(program.body.body[2].lhs.rhs.var, bar)
        CodeGenerator().generate(program)
        self.assertEqual((bar.offset, foo.offset, program.stack_size), (-8, -16, 16))
        another = parse_body("int foo=1; return foo;")
        self.assertIsNot(another.locals[0], foo)
        for source, offsets, size in [
            ("1;", [], 0), ("int x;", [-8], 16),
            ("int a,b,c;", [-8,-16,-24], 32),
            ("int a,b,c,d;", [-8,-16,-24,-32], 32),
        ]:
            program = parse_body(source)
            assembly = CodeGenerator().generate(program)
            self.assertEqual([var.offset for var in program.locals], offsets)
            self.assertEqual(program.stack_size, size)
            self.assertIn(f"  sub ${size}, %rsp\n", assembly)

    def test_statement_list(self):
        statements = parse_body("1; 2+3;")
        self.assertEqual(statements.body.body, [
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
                self.assertEqual(parse_body(source), Function(Node("BLOCK"), []))
                result = compile_program("{" + source + "}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(result.stdout, PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

    def test_tokenization(self):
        self.assertEqual(tokenize("if else ifx elsewhere"), [
            Token("KEYWORD", "if", 0), Token("KEYWORD", "else", 3),
            Token("IDENT", "ifx", 8), Token("IDENT", "elsewhere", 12),
            Token("EOF", "", 21),
        ])
        self.assertEqual(tokenize("return returnx return_ Return"), [
            Token("KEYWORD", "return", 0), Token("IDENT", "returnx", 7),
            Token("IDENT", "return_", 15), Token("IDENT", "Return", 23),
            Token("EOF", "", 29),
        ])
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
                statements = parse_body(source)
                self.assertEqual(statements.body.body, [Node("EXPR_STMT", lhs=expected)])
                generator = CodeGenerator()
                generator.generate(statements)
                self.assertEqual(generator.depth, 0)

    def test_exact_assembly(self):
        cases = [
            ("if(1) 2; else 3;", "  mov $1, %rax\n  cmp $0, %rax\n"
             "  je  .L.else.1\n  mov $2, %rax\n  jmp .L.end.1\n"
             ".L.else.1:\n  mov $3, %rax\n.L.end.1:\n"),
            ("if(0) ;", "  mov $0, %rax\n  cmp $0, %rax\n"
             "  je  .L.else.1\n  jmp .L.end.1\n.L.else.1:\n.L.end.1:\n"),
            ("return 3; 42;", "  mov $3, %rax\n  jmp .L.return\n  mov $42, %rax\n"),
            ("return 1; return 2;", "  mov $1, %rax\n  jmp .L.return\n"
             "  mov $2, %rax\n  jmp .L.return\n"),
            ("int a; a=3; a;", "  lea -8(%rbp), %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  mov %rax, (%rdi)\n  lea -8(%rbp), %rax\n  mov (%rax), %rax\n"),
            ("int z; z=5;", "  lea -8(%rbp), %rax\n  push %rax\n  mov $5, %rax\n"
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
                result = compile_program("{" + source + "}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                stack_size = 16 if source in ("int a; a=3; a;", "int z; z=5;") else 0
                self.assertEqual(result.stdout, PROLOGUE + f"  sub ${stack_size}, %rsp\n" + instructions + EPILOGUE)

    def test_executable_exit_status(self):
        # All current upstream examples and earlier arithmetic/control regressions.
        cases = [
            ('{ return 0; }', 0),
            ('{ return 42; }', 42),
            ('{ return 5+20-4; }', 21),
            ('{ return  12 + 34 - 5 ; }', 41),
            ('{ return 5+6*7; }', 47),
            ('{ return 5*(9-6); }', 15),
            ('{ return (3+5)/2; }', 4),
            ('{ return -10+20; }', 10),
            ('{ return - -10; }', 10),
            ('{ return - - +10; }', 10),
            ('{ return 0==1; }', 0),
            ('{ return 42==42; }', 1),
            ('{ return 0!=1; }', 1),
            ('{ return 42!=42; }', 0),
            ('{ return 0<1; }', 1),
            ('{ return 1<1; }', 0),
            ('{ return 2<1; }', 0),
            ('{ return 0<=1; }', 1),
            ('{ return 1<=1; }', 1),
            ('{ return 2<=1; }', 0),
            ('{ return 1>0; }', 1),
            ('{ return 1>1; }', 0),
            ('{ return 1>2; }', 0),
            ('{ return 1>=0; }', 1),
            ('{ return 1>=1; }', 1),
            ('{ return 1>=2; }', 0),
            ('{ int a; a=3; return a; }', 3),
            ('{ int a=3; return a; }', 3),
            ('{ int a=3; int z=5; return a+z; }', 8),
            ('{ int a; int b; a=b=3; return a+b; }', 6),
            ('{ int foo=3; return foo; }', 3),
            ('{ int foo123=3; int bar=5; return foo123+bar; }', 8),
            ('{ return 1; 2; 3; }', 1),
            ('{ 1; return 2; 3; }', 2),
            ('{ 1; 2; return 3; }', 3),
            ('{ {1; {2;} return 3;} }', 3),
            ('{ ;;; return 5; }', 5),
            ('{ if (0) return 2; return 3; }', 3),
            ('{ if (1-1) return 2; return 3; }', 3),
            ('{ if (1) return 2; return 3; }', 2),
            ('{ if (2-1) return 2; return 3; }', 2),
            ('{ if (0) { 1; 2; return 3; } else { return 4; } }', 4),
            ('{ if (1) { 1; 2; return 3; } else { return 4; } }', 3),
            ('{ int i=0; int j=0; for (i=0; i<=10; i=i+1) j=i+j; return j; }', 55),
            ('{ for (;;) return 3; return 5; }', 3),
            ('{ int i=0; while(i<10) i=i+1; return i; }', 10),
            ('{ int i=0; int j=0; while(i<=10) {j=i+j; i=i+1;} return j; }', 55),
            ('{ int x=3; return *&x; }', 3),
            ('{ int x=3; int *y=&x; int **z=&y; return **z; }', 3),
            ('{ int x=3; int y=5; return *(&x+1); }', 5),
            ('{ int x=3; int y=5; return *(&y-1); }', 3),
            ('{ int x=3; int y=5; return *(&x-(-1)); }', 5),
            ('{ int x=3; int *y=&x; *y=5; return x; }', 5),
            ('{ int x=3; int y=5; *(&x+1)=7; return y; }', 7),
            ('{ int x=3; int y=5; *(&y-2+1)=7; return x; }', 7),
            ('{ int x=3; return (&x+2)-&x+3; }', 5),
            ('{ int x, y; x=3; y=5; return x+y; }', 8),
            ('{ int x=3, y=5; return x+y; }', 8),
            ('{if (0) return 2; return 3;}', 3),
            ('{if (1-1) return 2; return 3;}', 3),
            ('{if (1) return 2; return 3;}', 2),
            ('{if (2-1) return 2; return 3;}', 2),
            ('{if (0) {1; 2; return 3;} else {return 4;}}', 4),
            ('{if (1) {1; 2; return 3;} else {return 4;}}', 3),
            ('{if(-3) return 7; else return 9;}', 7),
            ('{if(256) return 7; return 9;}', 7),
            ('{int a; a=0; if(1) a=3; else a=8; return a;}', 3),
            ('{int a; a=0; if(0) a=3; else a=8; return a;}', 8),
            ('{if(1) if(0) return 2; else return 3; return 4;}', 3),
            ('{if(0) if(1) return 2; else return 3; return 4;}', 4),
            ('{if(0) {if(1) return 2;} else return 3;}', 3),
            ('{if(0) return 1; else if(0) return 2; else return 3;}', 3),
            ('{int a; a=0; if(a=5) a=a+2; if(a==7) a=a*2; return a;}', 14),
            ('{if(1); else return 2; return 3;}', 3),
            ('{int ifx, elsewhere; ifx=3; elsewhere=4; if(ifx<elsewhere) return 8; return 9;}', 8),
            ('{;;; return 5;}', 5),
            ('{1;;}', 1),
            ('{int a; a=3;; {;; a=a+2;;}; return a;;}', 5),
            ('{return 7;;;;}', 7),
            ('{{1; {2;} return 3;}}', 3),
            ('{{} return 7;}', 7),
            ('{{{return 5;}} return 9;}', 5),
            ('{int a, b; a=1; {a=4; b=3;} return a+b;}', 7),
            ('{int a; a=2; {a=a*3; {a=a+4;}} return a;}', 10),
            ('{{{{}}} return 8;}', 8),
            ('{return 0;}', 0),
            ('{return 42;}', 42),
            ('{return 5+20-4;}', 21),
            ('{return  12 + 34 - 5 ;}', 41),
            ('{return 5+6*7;}', 47),
            ('{return 5*(9-6);}', 15),
            ('{return (3+5)/2;}', 4),
            ('{return -10+20;}', 10),
            ('{return - -10;}', 10),
            ('{return - - +10;}', 10),
            ('{return 0==1;}', 0),
            ('{return 42==42;}', 1),
            ('{return 0!=1;}', 1),
            ('{return 42!=42;}', 0),
            ('{return 0<1;}', 1),
            ('{return 1<1;}', 0),
            ('{return 2<1;}', 0),
            ('{return 0<=1;}', 1),
            ('{return 1<=1;}', 1),
            ('{return 2<=1;}', 0),
            ('{return 1>0;}', 1),
            ('{return 1>1;}', 0),
            ('{return 1>2;}', 0),
            ('{return 1>=0;}', 1),
            ('{return 1>=1;}', 1),
            ('{return 1>=2;}', 0),
            ('{int a; a=3; return a;}', 3),
            ('{int a, z; a=3; z=5; return a+z;}', 8),
            ('{int a, b; a=b=3; return a+b;}', 6),
            ('{int foo; foo=3; return foo;}', 3),
            ('{int foo123, bar; foo123=3; bar=5; return foo123+bar;}', 8),
            ('{return 1; 2; 3;}', 1),
            ('{1; return 2; 3;}', 2),
            ('{1; 2; return 3;}', 3),
            ('{return 1; return 2;}', 1),
            ('{int foo; foo=7; return (foo+5)*(foo-2); foo=99;}', 60),
            ('{int total; return total=9; total=0;}', 9),
            ('{int returnx, return_, Return; returnx=3; return_=4; Return=5; return returnx+return_+Return;}', 12),
            ('{return(3+4);}', 7),
            ('{return -7;}', 249),
            ('{int foo; foo=3; foo;}', 3),
            ('{int foo123, bar; foo123=3; bar=5; foo123+bar;}', 8),
            ('{int foo, foo123; foo=3; foo123=7; foo+foo123;}', 10),
            ('{int Foo, foo; Foo=3; foo=7; Foo+foo;}', 10),
            ('{int _, _value1; _=2; _value1=5; _+_value1;}', 7),
            ('{int total, left, right; total=left=right=4; total+left+right;}', 12),
            ('{int count; count=3; count=count+4; count;}', 7),
            ('{int alpha, beta, gamma; alpha=1; beta=2; gamma=3; alpha+beta+gamma;}', 6),
            ('{int a; a=3; a;}', 3),
            ('{int a, z; a=3; z=5; a+z;}', 8),
            ('{int a, b; a=b=3; a+b;}', 6),
            ('{int a; a=1; a=a+2; a;}', 3),
            ('{int a, b; a=4; b=7; a=9; b;}', 7),
            ('{int a; a=5==5; a;}', 1),
            ('{int a; a=3; (a=7)+2;}', 9),
            ('{int a, b; a=-(3+4); b=2; a/b;}', 253),
            ('{int a; (a)=6; a;}', 6),
            ('{int a; a=65536*65536; a/65536/65536;}', 1),
            ('{int a, z; a=2; z=8; (a+z)*(z-a); a+z;}', 10),
            ('{1; 2; 3;}', 3),
            ('{42; 0;}', 0),
            ('{1+2; 3*(4+5); (10-3)/2;}', 3),
            ('{5<6; -7;}', 249),
            ('{10;\n 20+22;\n}', 42),
            ('{0;}', 0),
            ('{42;}', 42),
            ('{5+20-4;}', 21),
            ('{ 12 + 34 - 5 ;}', 41),
            ('{5+6*7;}', 47),
            ('{5*(9-6);}', 15),
            ('{(3+5)/2;}', 4),
            ('{255;}', 255),
            ('{256;}', 0),
            ('{ 0042 ;}', 42),
            ('{2147483647;}', 255),
            ('{10-3-2;}', 5),
            ('{0-1;}', 255),
            ('{255+2;}', 1),
            ('{5+ 20-4;}', 21),
            ('{5 +20-4;}', 21),
            ('{\t12\n+\r34\x0b-\x0c5 ;}', 41),
            ('{1\u2003+\u20032;}', 3),
            ('{1+2147483647;}', 0),
            ('{0-2147483647-1;}', 0),
            ('{(5+6)*7;}', 77),
            ('{20/3;}', 6),
            ('{20/2/2;}', 5),
            ('{20/(2/2);}', 20),
            ('{24/3*2;}', 16),
            ('{24/(3*2);}', 4),
            ('{20-3*4+8/2;}', 12),
            ('{((2+3)*(4+(8/2)));}', 40),
            ('{((42));}', 42),
            ('{(0-7)/2;}', 253),
            ('{7/(0-2);}', 253),
            ('{(0-7)/(0-2);}', 3),
            ('{(0-3)*4;}', 244),
            ('{100/(2+3*(4-2));}', 12),
            ('{65536*65536/65536/65536;}', 1),
            ('{-10+20;}', 10),
            ('{- -10;}', 10),
            ('{- - +10;}', 10),
            ('{-1;}', 255),
            ('{+42;}', 42),
            ('{1+-2;}', 255),
            ('{1--2;}', 3),
            ('{1++2;}', 3),
            ('{1 + +2;}', 3),
            ('{-(3+4)*2;}', 242),
            ('{2*-(3+4);}', 242),
            ('{-20/3;}', 250),
            ('{20/-3;}', 250),
            ('{-20/-3;}', 6),
            ('{3*-4+15;}', 3),
            ('{-(-(-5));}', 251),
            ('{-2147483647-1;}', 0),
            ('{0==1;}', 0),
            ('{42==42;}', 1),
            ('{0!=1;}', 1),
            ('{42!=42;}', 0),
            ('{0<1;}', 1),
            ('{1<1;}', 0),
            ('{2<1;}', 0),
            ('{0<=1;}', 1),
            ('{1<=1;}', 1),
            ('{2<=1;}', 0),
            ('{1>0;}', 1),
            ('{1>1;}', 0),
            ('{1>2;}', 0),
            ('{1>=0;}', 1),
            ('{1>=1;}', 1),
            ('{1>=2;}', 0),
            ('{-1<0;}', 1),
            ('{0>-1;}', 1),
            ('{-2<=-1;}', 1),
            ('{-1>=0;}', 0),
            ('{2147483647+1>0;}', 1),
            ('{5+6*7==47;}', 1),
            ('{5+6*7!=47;}', 0),
            ('{5==2+3;}', 1),
            ('{3<4==1;}', 1),
            ('{3==4<5;}', 0),
            ('{1<2<3;}', 1),
            ('{3>2>0;}', 1),
            ('{(3>2)+4;}', 5),
            ('{(5>=5)*7;}', 7),
            ('{1==1==1;}', 1),
            ('{2==2==2;}', 0),
            ("{" + "".join(f"int var{i}={i};" for i in range(30))
             + "+".join(f"var{i}" for i in range(30)) + ";}", 179),
            ("{" + "".join(f"int {chr(97+i)}={i+1};" for i in range(26))
             + "+".join(chr(97+i) for i in range(26)) + ";}", 95),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)

    def test_invalid_arguments(self):
        cases = [(), ("1", "2"), ("abc",), ("42abc",),
                 ("1_000",), ("2147483648",), ("-2147483649",),
                 ("1+",), ("1-",), ("1+abc",), ("1+2junk",), ("1 2",),
                 ("1+2147483648",), ("1-2147483649",),
                 ("1 + ",), ("１２",), ("()",), ("(1",), ("1)",),
                 ("2(3)",), ("1//2",), ("1/",), ("1%2",),
                 ("+",), ("-",), ("--",), ("1*-",),
                 ("1=1",), ("1!2",), ("1<",), ("1>=",),
                 ("1===1",), ("1<>2",), ("1&&2",)]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                if len(arguments) == 1:
                    arguments = ("{" + arguments[0] + "}",)
                result = compile_program(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_error_messages(self):
        cases = [
            ("if 1;", "if 1;\n   ^ expected '('\n"),
            ("if(1 return 2;", "if(1 return 2;\n     ^ expected ')'\n"),
            ("if() return 2;", "if() return 2;\n   ^ expected an expression\n"),
            ("else return 1;", "else return 1;\n^ expected an expression\n"),
            ("if(1)", "if(1)\n     ^ expected an expression\n"),
            ("if(0) 1=2; return 3;", "if(0) 1=2; return 3;\n      ^ not an lvalue\n"),
            ("return;", "return;\n      ^ expected an expression\n"),
            ("return 1", "return 1\n        ^ expected ';'\n"),
            ("return=1;", "return=1;\n      ^ expected an expression\n"),
            ("return 1; 2", "return 1; 2\n           ^ expected ';'\n"),
            ("return 1; 1=3;", "return 1; 1=3;\n          ^ not an lvalue\n"),
            ("42", "42\n  ^ expected ';'\n"),
            ("1; 2", "1; 2\n    ^ expected ';'\n"),
            ("1; 2+;", "1; 2+;\n     ^ expected an expression\n"),
            ("1; (2;", "1; (2;\n     ^ expected ')'\n"),
            ("1@2", "1@2\n ^ expected ';'\n"),
            ("1+", "1+\n  ^ expected an expression\n"),
            (" 12 +   ", " 12 +   \n        ^ expected an expression\n"),
            ("18 11", "18 11\n   ^ expected ';'\n"),
            ("--", "--\n  ^ expected an expression\n"),
            ("1 + +", "1 + +\n     ^ expected an expression\n"),
            ("1+2147483648", "1+2147483648\n  ^ integer must fit in a signed 32-bit immediate\n"),
            ("1\u2003+@", "1\u2003+@\n   ^ expected an expression\n"),
            ("(1+2", "(1+2\n    ^ expected ')'\n"),
            ("1)", "1)\n ^ expected ';'\n"),
            ("()", "()\n ^ expected an expression\n"),
            ("1/", "1/\n  ^ expected an expression\n"),
            ("(1 2)", "(1 2)\n   ^ expected ')'\n"),
            ("1=1;", "1=1;\n^ not an lvalue\n"),
            ("é=3;", "é=3;\n^ invalid token\n"),
            ("1<", "1<\n  ^ expected an expression\n"),
            ("1>=", "1>=\n   ^ expected an expression\n"),
            ("1===1", "1===1\n   ^ expected an expression\n"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                result = compile_program("{" + source + "}")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                if expected.startswith(source + "\n"):
                    expected = "{" + source + "}\n " + expected[len(source) + 1:]
                self.assertEqual(result.stderr, expected)

    def test_argument_error_has_no_source_location(self):
        for arguments in [(), ("1", "2")]:
            with self.subTest(arguments=arguments):
                result = compile_program(*arguments)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, f"{COMPILER}: invalid number of arguments\n")

    def test_declarations(self):
        for source, expected in [
            ("{int; return 7;}", 7),
            ("{int x=3,y=x+2; return x+y;}", 8),
            ("{int x=3,*p=&x; *p=7; return x;}", 7),
            ("{int a,b; a=b=3; return a+b;}", 6),
            ("{int integer=5; return integer;}", 5),
            ("{int x=1; {int y=4;} return x+y;}", 5),
            ("{int x=1; {int x=4;} return x;}", 4),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("int x=3, *p=&x, **q=&p; return **q;")
        q, p, x = program.locals
        self.assertEqual([q.ty.kind, p.ty.kind, x.ty.kind], ["PTR", "PTR", "INT"])
        self.assertEqual(q.ty.base.kind, "PTR")
        self.assertEqual(q.ty.base.base.kind, "INT")
        self.assertEqual([var.ty.name.text for var in [q,p,x]], ["q","p","x"])
        self.assertIsNone(ty_int.name)
        declaration = program.body.body[0]
        self.assertEqual(declaration.kind, "BLOCK")
        self.assertEqual(len(declaration.body), 3)
        for statement in declaration.body:
            self.assertEqual(statement.kind, "EXPR_STMT")
            self.assertEqual(statement.lhs.kind, "ASSIGN")
        program = parse_body("int a,b; a=b=3;")
        assignment = program.body.body[1].lhs
        self.assertEqual(assignment.kind, "ASSIGN")
        self.assertEqual(assignment.rhs.kind, "ASSIGN")
        result = compile_program("{int x; return 7;}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, PROLOGUE + "  sub $16, %rsp\n"
                         "  mov $7, %rax\n  jmp .L.return\n" + EPILOGUE)
        self.assertEqual(tokenize("int integer")[0].kind, "KEYWORD")
        self.assertEqual(tokenize("int integer")[1].kind, "IDENT")

    def test_declaration_errors(self):
        cases = [
            ("{x=3;}", 1, "undefined variable"),
            ("{return x; int x;}", 8, "undefined variable"),
            ("{int x=y;}", 7, "undefined variable"),
            ("{int 3;}", 5, "expected a variable name"),
            ("{int *;}", 6, "expected a variable name"),
            ("{int x y;}", 7, "expected ','"),
            ("{int x,;}", 7, "expected a variable name"),
            ("{int x=;}", 7, "expected an expression"),
            ("{for(int i=0;;);}", 5, "expected an expression"),
            ("{return *1;}", 8, "invalid pointer dereference"),
            ("{int x=3; return *x;}", 17, "invalid pointer dereference"),
            ("{int x,y; return &x+&y;}", 19, "invalid operands"),
            ("{int x; return 1-&x;}", 16, "invalid operands"),
            ("{int x; (x+1)=3;}", 10, "not an lvalue"),
        ]
        for source, position, message in cases:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, source + "\n" + " " * position
                                 + "^ " + message + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
