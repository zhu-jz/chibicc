"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
from dataclasses import replace
import subprocess
import sys
import tempfile
import unittest

from codegen import CodeGenerator
from common import CompileError, Node, Obj, Token
from parse import parse
from tokenizer import tokenize
from type import ty_int, ty_long, ty_short, ty_void


COMPILER = Path(__file__).with_name("main.py")
PROLOGUE = "  .globl main\n  .text\nmain:\n  push %rbp\n  mov %rsp, %rbp\n"
EPILOGUE = ".L.return.main:\n  mov %rbp, %rsp\n  pop %rbp\n  ret\n"


def compile_program(*arguments):
    """Feed in-memory source fixtures to the compiler through stdin."""
    if len(arguments) == 1:
        return subprocess.run([sys.executable, str(COMPILER), "-"],
                              input=arguments[0], capture_output=True, text=True)
    return subprocess.run(
        [sys.executable, str(COMPILER), *arguments],
        capture_output=True,
        text=True,
    )


def parse_body(source):
    """Parse a main function containing a statement-body fixture."""
    return parse(tokenize('int main(){' + source + "}"))[0]


def instruction_assembly(assembly):
    """Keep instruction snapshots independent of source-debug metadata."""
    return "".join(line for line in assembly.splitlines(keepends=True)
                   if not line.lstrip().startswith((".file ", ".loc ")))


def without_implicit_casts(node):
    """Compare grammar trees; separate tests check the inserted conversions."""
    if isinstance(node, list):
        return [without_implicit_casts(child) for child in node]
    if isinstance(node, Obj):
        return replace(node, body=without_implicit_casts(node.body))
    if not isinstance(node, Node):
        return node
    if node.kind == "CAST" and node.tok is node.lhs.tok:
        return without_implicit_casts(node.lhs)
    children = {name: without_implicit_casts(getattr(node, name))
                for name in ("lhs", "rhs", "cond", "then", "els", "init", "inc", "body", "args")}
    return replace(node, **children)


class ExpressionCompilerTests(unittest.TestCase):
    def test_static_functions(self):
        source = "static int f(){return 42;}int main(){return f();}"
        self.assert_program_returns(source, 42, "static int f(){return 5;}")
        assembly = compile_program(source).stdout
        self.assertIn("  .local f\n", assembly)
        self.assertNotIn("  .globl f\n", assembly)
        self.assertIn("  .globl main\n", assembly)
        prototype = parse(tokenize("int static f();"))[0]
        self.assertTrue(prototype.is_static)
        self.assertFalse(prototype.is_definition)
        for source, message in [
            ("typedef static int T;", "typedef and static may not be used together"),
            ("static typedef int T;", "typedef and static may not be used together"),
            ("int f(static int x);", "storage class specifier is not allowed"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_enum_types(self):
        for source, expected in [
            ("enum E{zero,five=5,six};int main(){enum E x=six;return x;}", 6),
            ("int main(){enum {a=3,b,c=1,d};return b+d;}", 6),
            ("enum E{a=5};int main(){{enum E{a=9};}return a;}", 5),
            ("enum {a=5};int main(){int a=42;return a;}", 42),
            ("int main(){enum {a} x;return sizeof(x);}", 4),
        ]:
            self.assert_program_returns(source, expected)
        function = parse(tokenize("enum {answer=42};int main(){return answer;}"))[0]
        self.assertEqual(function.locals, [])
        self.assertIn("  mov $42, %rax\n", compile_program("enum {answer=42};int main(){return answer;}").stdout)
        for source, message in [
            ("enum Missing x;", "unknown enum type"),
            ("struct E{int a;};enum E x;", "not an enum tag"),
            ("enum {a=-1};", "expected a number"),
            ("enum {a,};", "expected a variable name"),
            ("int main(){{enum {a};}return a;}", "undefined variable"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_character_literals(self):
        for spelling, value in [("'a'", 97), (r"'\n'", 10), (r"'\x80'", -128),
                                (r"'\377'", -1), (r"'\''", 39), ("'ab'", 97)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.kind, token.text, token.value), ("NUM", spelling, value))
            self.assert_program_returns(f"int main(){{return {spelling};}}", value & 255)
        self.assert_program_returns(r"int main(){return '\x80'<0;}", 1)
        self.assert_program_returns("int main(){return sizeof('a');}", 4)
        self.assertIn("  mov $97, %rax\n", compile_program("int main(){return 'a';}").stdout)
        for source in ["'", "'a", "'\\"]:
            with self.assertRaises(CompileError) as error:
                tokenize(source)
            self.assertIn("unclosed char literal", str(error.exception))

    def test_bool_type(self):
        for source, expected in [
            ("int main(){_Bool x=256;return x;}", 1),
            ("int main(){return (_Bool)0;}", 0),
            ("int main(){return (_Bool)(char)256;}", 0),
            ("int main(){return (_Bool)4294967296;}", 1),
            ("int main(){int x;return (_Bool)&x;}", 1),
            ("_Bool f(_Bool x){return x+1;}int main(){return f(0);}", 1),
            ("int main(){_Bool x;return sizeof(x)+sizeof(x+1);}", 5),
        ]:
            self.assert_program_returns(source, expected)
        for value, register in ((256, "%eax"), (4294967296, "%rax")):
            assembly = compile_program(f"int main(){{return (_Bool){value};}}").stdout
            self.assertIn(f"  cmp $0, {register}\n", assembly)
            self.assertIn("  setne %al\n  movzx %al, %eax\n", assembly)
        self.assertEqual(tokenize("_Bool")[0].kind, "KEYWORD")

    def test_argument_conversions(self):
        for source, expected in [
            ("int f(long a,long b){return a/b;}int main(){return f(-10,2)==-5;}", 1),
            ("int f(char x){return x;}int main(){return f(261);}", 5),
            ("int f(short x){return x<0;}int main(){return f(65535);}", 1),
        ]:
            self.assert_program_returns(source, expected)
        call = parse(tokenize("int f(long x);int main(){return f(-1);}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.func_ty.kind, "FUNC")
        self.assertEqual((call.args[0].kind, call.args[0].ty.kind), ("CAST", "LONG"))
        assembly = compile_program("int f(long x);int main(){return f(-1);}").stdout
        self.assertIn("  movsxd %eax, %rax\n", assembly)
        for kind in ("struct", "union"):
            result = compile_program(f"{kind} T{{int x;}};int f({kind} T x);int main(){{{kind} T a;return f(a);}}")
            self.assertIn("passing struct or union is not supported yet", result.stderr)
            self.assertEqual(result.returncode, 1)

    def test_return_conversions(self):
        for source, expected in [
            ("char f(int x){return x;}int main(){return f(261);}", 5),
            ("short f(){return 65535;}int main(){return f()<0;}", 1),
            ("long f(){return -1;}int main(){return f()<0;}", 1),
            ("int x;int *f(){return &x;}int main(){x=42;return *f();}", 42),
        ]:
            self.assert_program_returns(source, expected)
        node = parse(tokenize("char f(){return 261;}"))[0].body.body[0].lhs
        self.assertEqual((node.kind, node.ty.kind, node.lhs.kind), ("CAST", "CHAR", "NUM"))
        assembly = compile_program("char f(){return 261;}").stdout
        self.assertIn("  movsbl %al, %eax\n  jmp .L.return.f", assembly)

    def test_declared_calls(self):
        self.assert_program_returns("int f();int main(){return f();}int f(){return 42;}", 42)
        call = parse(tokenize("char f();int main(){return f();}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.ty.kind, "CHAR")
        self.assert_program_returns("int f(int x){if(x==0)return 42;return f(x-1);}int main(){return f(3);}", 42)
        for source, message in [
            ("int main(){return missing();}", "implicit declaration of a function"),
            ("int main(){int f;return f();}", "not a function"),
            ("typedef int f;int main(){return f();}", "not a function"),
            ("int f();int main(){int f;return f();}", "not a function"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_usual_arithmetic_conversions(self):
        for source, expected in [
            ("int main(){int x=-10;long y=5;return (x+y)==-5;}", 1),
            ("int main(){char x=-1;short y=2;return sizeof(x+y);}", 4),
            ("int main(){char x=-1;long y=2;return x+y;}", 1),
            ("int main(){long x=(int)4294967295;return x<0;}", 1),
            ("int main(){int a[2];a[0]=42;int i=-1;int *p=a+1;return p[i];}", 42),
            ("int main(){return sizeof(1)+sizeof(1==2);}", 8),
            ("int main(){return 1073741824*100/100;}", 0),
        ]:
            self.assert_program_returns(source, expected)
        node = parse_body("int x;long y;return x+y;").body.body[-1].lhs.lhs
        self.assertEqual((node.ty.kind, node.lhs.kind, node.rhs.kind), ("LONG", "CAST", "CAST"))
        self.assertEqual((node.lhs.lhs.ty.kind, node.lhs.ty.kind), ("INT", "LONG"))
        comparison = parse_body("return 1<2;").body.body[0].lhs.lhs
        self.assertEqual(comparison.ty.kind, "INT")
        assignment = parse_body("long x; x=-1;").body.body[-1].lhs
        self.assertEqual((assignment.rhs.kind, assignment.rhs.ty.kind), ("CAST", "LONG"))
        self.assertIs(parse_body("return 2147483648;").body.body[0].lhs.lhs.ty, ty_long)
        assembly = compile_program("int main(){char x=-1;long y=x;return y<0;}").stdout
        self.assertIn("  movsbl (%rax), %eax\n", assembly)
        self.assertIn("  movsxd %eax, %rax\n", assembly)

    def test_explicit_casts(self):
        for source, expected in [
            ("int main(){return (long)(short)65535<0;}", 1),
            ("int main(){return (long)(char)255<0;}", 1),
            ("int main(){int x=-1;return (long)x<0;}", 1),
            ("int main(){int x=0;(void)(x=7);return x;}", 7),
            ("typedef int T;int main(){return (T)42;}", 42),
            ("typedef int T;int main(){long T=3;return (T)+1;}", 4),
            ("int main(){int a[2];a[0]=42;int i=-1;int *p=a+1;return *(p+(long)i);}", 42),
            ("int main(){return sizeof((short)1);}", 2),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(){return (long)(short)(char)255;}").stdout
        self.assertIn("  movsbl %al, %eax\n", assembly)
        self.assertIn("  movsxd %eax, %rax\n", assembly)
        node = parse_body("return (short)1;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.ty.kind, node.lhs.ty.kind, node.tok.text),
                         ("CAST", "SHORT", "INT", "("))
        for source in ["int main(){return (int 1;}", "int main(){return (int);}"]:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_binary_register_widths(self):
        for spelling in ["int", "long"]:
            source = "int main(){" + spelling + " x=7,y=3;return (x+y)*(x-y)/y;}"
            self.assert_program_returns(source, 13)
            assembly = compile_program(source).stdout
            ax, di = ("%eax", "%edi") if spelling == "int" else ("%rax", "%rdi")
            for instruction in ["add", "sub", "imul"]:
                self.assertIn(f"  {instruction} {di}, {ax}\n", assembly)
            extension = "cdq" if spelling == "int" else "cqo"
            self.assertIn(f"  {extension}\n  idiv {di}\n", assembly)
        for spelling in ["char", "short", "int", "long"]:
            self.assert_program_returns("int main(){" + spelling + " x=-7;return x/2;}", 253)
            assembly = compile_program("int main(){" + spelling + " x=3;return x<4;}").stdout
            comparison = "  cmp %rdi, %rax\n" if spelling == "long" else "  cmp %edi, %eax\n"
            self.assertIn(comparison, assembly)
        self.assert_program_returns("int main(){int x=65536;return x*x;}", 0)
        assembly = compile_program("int main(){int x;int *p=&x;return (p+1)-p;}").stdout
        self.assertIn("  add %rdi, %rax\n", assembly)
        self.assertIn("  sub %rdi, %rax\n", assembly)
        self.assertIn("  cdq\n  idiv %edi\n", assembly)

    def test_sizeof_type_names(self):
        for source, expected in [
            ("typedef int T;int main(){return sizeof(T);}", 4),
            ("typedef char T;int main(){long T;return sizeof(T);}", 8),
            ("int main(){return sizeof(void);}", 1),
            ("int main(){return sizeof(long long int);}", 8),
            ("int main(){return sizeof(int(**)[3]);}", 8),
            ("int main(){return sizeof(int(*[2])[3]);}", 16),
            ("int main(){return sizeof(int (*)(int x));}", 8),
        ]:
            self.assert_program_returns(source, expected)
        actual = compile_program("int main(){return sizeof(int*[4]);}")
        expected = compile_program("int main(){return 32;}")
        self.assertEqual(instruction_assembly(actual.stdout), instruction_assembly(expected.stdout))
        for source, message in [
            ("int main(){return sizeof(int[3]);}", None),
            ("int main(){return sizeof(int[3];}", "expected ')'"),
            ("int main(){return sizeof(typedef int T);}", "storage class specifier is not allowed in this context"),
        ]:
            result = compile_program(source)
            if message is None:
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_typedefs(self):
        for source, expected in [
            ("typedef int Row[3];int main(){Row a[2];Row *p=a;p[1][2]=42;return a[1][2];}", 42),
            ("typedef long L;L twice(L x){return x+x;}int main(){return twice(2147483648)/65536/65536;}", 1),
            ("typedef int T;int main(){{int T=3;}T x=42;return x;}", 42),
            ("typedef int T;int main(){int T=3;{typedef char T;T c=2;}return T;}", 3),
            ("int main(){typedef int t;t t=3;return t;}", 3),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual(compile_program("typedef int T;").stdout, '.file 1 "-"\n')
        program = parse_body("typedef int T;T x=1;")
        self.assertEqual([var.name for var in program.locals], ["x"])
        for source, message in [
            ("int main(){{typedef int T;}T x;}", "undefined variable"),
            ("int main(){typedef int T;return T;}", "undefined variable"),
            ("struct s{typedef int T;};", "storage class specifier is not allowed in this context"),
            ("int f(typedef int x);", "storage class specifier is not allowed in this context"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_long_long_alias(self):
        for spelling in ["long long", "long long int", "int long long", "long int long"]:
            self.assert_program_returns("int main(){" + spelling + " x;return sizeof(x);}", 8)
            ty = parse_body(spelling + " x;").locals[0].ty
            self.assertEqual((ty.kind, ty.size, ty.align), ("LONG", 8, 8))
        self.assert_program_returns("int main(){long long x=4294967296;return x/65536/65536;}", 1)
        for spelling in ["long long long", "long long int int", "short long long"]:
            result = compile_program("int main(){" + spelling + " x;}")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid type", result.stderr)

    def test_type_specifier_combinations(self):
        for spelling, size in [("char", 1), ("short int", 2), ("int short", 2),
                               ("int", 4), ("long int", 8), ("int long", 8)]:
            self.assert_program_returns("int main(){" + spelling + " x;return sizeof(x);}", size)
        self.assert_program_returns("main(){return 42;}", 42)
        self.assert_program_returns("int f(x){return x;}main(){return f(42);}", 42)
        for spelling in ["char int", "int int", "void int", "short long"]:
            result = compile_program("int main(){" + spelling + " x;}")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid type", result.stderr)

    def test_void_type(self):
        for source, expected in [
            ("int main(){void *p;return sizeof(p);}", 8),
            ("int main(){int x=42;void *p=&x;int *q=p;return *q;}", 42),
            ("void f();void f(){}int main(){f();return 42;}", 42),
            ("int main(){int x;void *p=&x;return (p+1)-p;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual((ty_void.size, ty_void.align), (1, 1))
        self.assertEqual(parse_body("void *p;").locals[0].ty.base.kind, "VOID")
        for source, message in [("int main(){void x;}", "variable declared void"),
                                ("int main(){void *p;return *p;}", "dereferencing a void pointer"),
                                ("int main(){void *p;sizeof(*p);}", "dereferencing a void pointer")]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn(message, result.stderr)

    def test_function_declarations(self):
        self.assert_program_returns("int f(int x);int main(){return f(42);}int f(int x){return x;}", 42)
        self.assert_program_returns("int ret42();int main(){return ret42();}", 42,
                                    "int ret42(void){return 42;}")
        program = parse(tokenize("int f(int x);int f(int x){return x;}"))
        self.assertEqual([obj.is_definition for obj in program], [True, False])
        self.assertTrue(all(obj.is_function for obj in program))
        self.assertIsNone(program[1].body)
        self.assertEqual(program[1].locals, [])
        assembly = compile_program("int f(int x);int f(int x){return x;}").stdout
        self.assertEqual(assembly.splitlines().count("f:"), 1)
        self.assertNotIn("  .data", assembly)
        self.assertEqual(compile_program("int printf();").stdout, '.file 1 "-"\n')
        self.assertEqual(compile_program("int f(int); ").returncode, 1)

    def test_nested_declarators(self):
        for source, expected in [
            ("int (main)(){return 42;}", 42),
            ("int main(){char *(*x[2])[3];return sizeof(x);}", 16),
            ("int main(){int a[2][3];int (*p)[3]=a;p[1][2]=42;return a[1][2];}", 42),
            ("int f(int (*p)[3]){return p[0][2];}int main(){int a[3];a[2]=42;return f(a);}", 42),
        ]:
            self.assert_program_returns(source, expected)
        array = parse_body("char *x[3];").locals[0].ty
        pointer = parse_body("char (*x)[3];").locals[0].ty
        self.assertEqual((array.kind, array.size, array.base.kind), ("ARRAY", 24, "PTR"))
        self.assertEqual((pointer.kind, pointer.size, pointer.base.kind, pointer.base.size),
                         ("PTR", 8, "ARRAY", 3))
        ty = parse_body("char (x[3])[4];").locals[0].ty
        self.assertEqual((ty.array_len, ty.base.array_len, ty.size), (3, 4, 12))
        self.assertEqual(ty.name.text, "x")
        result = compile_program("int main(){int (*x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected ')'", result.stderr)

    def test_short_type(self):
        for source, expected in [
            ("int main(){short x;return sizeof(x);}", 2),
            ("int main(){short x=32768;return x<0;}", 1),
            ("short g;int main(){g=65535;return g==-1;}", 1),
            ("int main(){short x=7;short y=9;x=11;return y;}", 9),
            ("int main(){short a[3];a[2]=42;return *(a+2);}", 42),
            ("int main(){struct {char a;short b;} x;return sizeof(x);}", 4),
            ("int f(short a,short b,short c,short d,short e,short f){return a+b+c+d+e+f;}int main(){return f(1,2,3,4,5,6);}", 21),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("short f(short a){return a;}int main(){short x=42;return f(x);}").stdout
        self.assertIn("  mov %di, -2(%rbp)\n", assembly)
        self.assertIn("  mov %ax, (%rdi)\n", assembly)
        self.assertIn("  movswl (%rax), %eax\n", assembly)
        self.assertEqual((ty_short.size, ty_short.align), (2, 2))

    def test_long_type(self):
        for source, expected in [
            ("int main(){long x=4294967296;return x/65536/65536;}", 1),
            ("long g;int main(){g=9223372036854775807;return g==9223372036854775807;}", 1),
            ("long f(long x){return x+1;}int main(){return f(4294967296)/65536/65536;}", 1),
            ("int main(){long a[2];a[0]=3;a[1]=4;return *(a+1);}", 4),
            ("int main(){struct {char a;long b;} x;return sizeof(x);}", 16),
            ("long missing();int main(){return sizeof(1)+sizeof(1==2)+sizeof(missing());}", 16),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("long f(long a){return a;}int main(){long x=4294967296;return f(x)/65536/65536;}").stdout
        self.assertIn("  mov $4294967296, %rax\n", assembly)
        self.assertIn("  mov %rdi, -8(%rbp)\n", assembly)
        self.assertIn("  mov %rax, (%rdi)\n", assembly)
        self.assertEqual((ty_long.size, ty_long.align), (8, 8))
        self.assertIs(parse_body("return 1;").body.body[0].lhs.lhs.ty, ty_int)
        self.assertEqual(tokenize("9223372036854775807")[0].value, 9223372036854775807)
        self.assertEqual(tokenize("short")[0].kind, "KEYWORD")
        result = compile_program("int main(){short x;}")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = compile_program("int main(){return 9223372036854775808;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("signed 64-bit immediate", result.stderr)

    def test_four_byte_ints(self):
        for source, expected in [
            ("int main(){int x;int *p=&x;return sizeof(x)+sizeof(p);}", 12),
            ("int main(){int x=2147483647+1;return x<0;}", 1),
            ("int main(){int x=65536*65536;return x;}", 0),
            ("int main(){int x=7;int y=9;x=11;return y;}", 9),
            ("int f(int x){return x<0;}int main(){return f(-1);}", 1),
            ("int f(char c,int x,int *p,int y,char d,int z){return c+x+*p+y+d+z;}int main(){int v=7;return f(1,2,&v,3,4,5);}", 22),
        ]:
            self.assert_program_returns(source, expected)
        self.assert_program_returns("int sum(int *a);int main(){int a[2];a[0]=3;a[1]=4;return sum(a);}", 7,
                                    "int sum(int *a){return a[0]+a[1];}")
        assembly = compile_program("int main(){int x=42;return x;}").stdout
        self.assertIn("  mov %eax, (%rdi)\n", assembly)
        self.assertIn("  movsxd (%rax), %rax\n", assembly)
        self.assertEqual((ty_int.size, ty_int.align), (4, 4))

    def test_aggregate_assignment(self):
        for source, expected in [
            ("int main(){struct t{int a,b;} x,y,z;x.a=3;x.b=7;z=y=x;return z.a+y.b;}", 10),
            ("int main(){struct t{char a[17];} x,y;x.a[16]=42;y=x;return y.a[16];}", 42),
            ("int main(){struct t{char a;int b;} x,y;char *p=&x;int i;for(i=0;i<sizeof(x);i=i+1)p[i]=i;y=x;char *q=&y;return q[7];}", 7),
            ("int main(){union t{int a;char b[4];} x,y;x.a=515;y=x;return y.b[1];}", 2),
            ("struct t{int a;} g;int main(){struct t x;x.a=42;g=x;return g.a;}", 42),
            ("int main(){struct t{int a;} x;x.a=42;x=x;struct t y=x;return y.a;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(){struct {char a[3];} x,y;y=x;return 0;}").stdout
        for offset in range(3):
            self.assertIn(f"  mov {offset}(%rax), %r8b\n  mov %r8b, {offset}(%rdi)\n", assembly)
        self.assertNotIn("  mov 3(%rax), %r8b", assembly)

    def test_unions(self):
        for source, expected in [
            ("int main(){union t{int a;char b[4];} x;union t *p=&x;p->a=515;return p->b[0]+p->b[1];}", 5),
            ("union t{int a;char b[4];};union t g;int main(){g.a=515;return g.b[1];}", 2),
            ("int main(){union t{int a;};{union t{char a;};}union t x;return sizeof(x);}", 4),
            ("int main(){union {int a;char b[9];} x[2];char *p=x;char *q=x+1;return q-p;}", 12),
        ]:
            self.assert_program_returns(source, expected)
        ty = parse_body("union {int a;char b[9];} x;").locals[0].ty
        self.assertEqual((ty.kind, ty.size, ty.align), ("UNION", 12, 4))
        self.assertEqual([member.offset for member in ty.members], [0, 0])
        ty = parse_body("struct {char a;union {int b;char c[9];} d;} x;").locals[0].ty
        self.assertEqual((ty.size, ty.members[1].offset), (16, 4))

    def test_member_arrow(self):
        for source, expected in [
            ("int main(){struct t{char a;} x;struct t *y=&x;x.a=3;return y->a;}", 3),
            ("int main(){struct t{char a;} x;struct t *y=&x;y->a=3;return x.a;}", 3),
            ("int main(){struct t{int a;} x[2];struct t *p=x;p[1].a=7;return (p+1)->a;}", 7),
            ("int main(){struct n{int v;} x;struct h{struct n *p;} y;struct h *z=&y;y.p=&x;z->p->v=42;return x.v;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        prefix = "int main(){struct t{int a;} x;struct t *p=&x;"
        arrow = compile_program(prefix + "return p->a;}")
        dot = compile_program(prefix + "return (*p).a;}")
        self.assertEqual(instruction_assembly(arrow.stdout), instruction_assembly(dot.stdout))
        self.assertEqual(tokenize("p->a")[1].text, "->")
        for source, message in [("int main(){int x;return x->a;}", "invalid pointer dereference"),
                                ("int main(){int x;int *p=&x;return p->a;}", "not a struct")]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_struct_tags(self):
        for source, expected in [
            ("struct t{int a;};struct t g;int main(){g.a=5;return g.a;}", 5),
            ("int main(){struct t{int a;};{struct t{char a;};struct t x;return sizeof(x);}}", 1),
            ("int main(){struct t{int a;};{struct t{char a;};}struct t x;return sizeof(x);}", 4),
            ("int main(){struct t{int a;};int t=3;struct t x;x.a=4;return t+x.a;}", 7),
        ]:
            self.assert_program_returns(source, expected)
        for source in ["int main(){struct missing x;}",
                       "int main(){{struct t{int a;};}struct t x;}",
                       "struct t{struct t *next;};"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unknown struct type", result.stderr)

    def test_local_alignment(self):
        for source, offsets, stack_size in [
            ("int x;char y;", [-1, -8], 16),
            ("char x;int y;", [-4, -5], 16),
            ("struct {char a;int b;} x;char y;", [-1, -12], 16),
        ]:
            program = parse_body(source)
            CodeGenerator().generate([program])
            self.assertEqual([var.offset for var in program.locals], offsets)
            self.assertEqual(program.stack_size, stack_size)
            for var in program.locals:
                self.assertEqual(var.offset % var.ty.align, 0)
        self.assert_program_returns("int main(){int x;int y;char z;char *a=&y;char *b=&z;return b-a;}", 7)
        self.assert_program_returns("int main(){int x;char y;int z;char *a=&y;char *b=&z;return b-a;}", 1)

    def test_struct_alignment(self):
        for declaration, size, alignment, offsets in [
            ("struct {char a;int b;char c;} x;", 12, 4, [0, 4, 8]),
            ("struct {char a;char b;} x;", 2, 1, [0, 1]),
            ("struct {} x;", 0, 1, []),
            ("struct {char a;struct {char b;int c;} d;} x;", 12, 4, [0, 4]),
        ]:
            ty = parse_body(declaration).locals[0].ty
            self.assertEqual((ty.size, ty.align), (size, alignment))
            self.assertEqual([member.offset for member in ty.members], offsets)
        self.assert_program_returns("int main(){struct {char a;int b;} x;char *p=&x;char *q=&x.b;return q-p;}", 4)
        self.assert_program_returns("int main(){struct {char a;int b;} x[2];char *p=x;char *q=x+1;return q-p;}", 8)
        ty = parse_body("struct {char a;int b;} x[2];").locals[0].ty
        self.assertEqual((ty.size, ty.align), (16, 4))

    def test_struct_members(self):
        for source, expected in [
            ("int main(){struct {char a;int b;char c;} x;x.a=1;x.b=2;x.c=3;return x.a+x.b+x.c;}", 6),
            ("struct {int a;char b;} g;int main(){g.a=7;g.b=3;return g.a+g.b;}", 10),
            ("int main(){struct {char a[3];char b;} x;x.a[2]=5;x.b=7;return x.a[2]+x.b;}", 12),
            ("int main(){struct {int a;} x;int *p=&x.a;*p=9;return x.a;}", 9),
        ]:
            self.assert_program_returns(source, expected)
        program = parse_body("struct {char a;int b;} x;return sizeof(x);")
        ty = program.locals[0].ty
        self.assertEqual(ty.size, 8)
        self.assertEqual([member.offset for member in ty.members], [0, 4])
        assembly = compile_program("int main(){struct {char a;int b;} x;x.b=42;return x.b;}")
        self.assertIn("  add $4, %rax\n", assembly.stdout)
        for source, message in [
            ("int main(){int x;return x.a;}", "not a struct"),
            ("int main(){struct {int x;} a;return a.y;}", "no such member"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_comma_operator(self):
        for source, expected in [
            ("int main(){return (1,2,3);}", 3),
            ("int main(){int i=2,j=3;(i=5,j)=6;return i;}", 5),
            ("int main(){int i=2,j=3;(i=5,j)=6;return j;}", 6),
            ("int main(){int x=0;return (x=1,x=x+2,x);}", 3),
            ("int main(){int i=0,j=2;*(i=5,&j)=6;return i+j;}", 11),
            ("int main(){char x;return sizeof(1,x);}", 1),
            ("int main(){int x=(1,2);return x;}", 2),
            ("int pair(int a,int b){return a+b;}int main(){int x=0;return pair((x=1,7),x);}", 8),
        ]:
            self.assert_program_returns(source, expected)
        node = parse_body("return 1,2,3;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.rhs.kind), ("COMMA", "COMMA"))
        self.assertIs(node.ty, ty_int)
        result = compile_program("int main(){(1,2)=3;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an lvalue", result.stderr)

    def test_assembly_source_locations(self):
        source_text = "int main(){\n return 42;\n}\n"
        result = compile_program(source_text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('.file 1 "-"\n'))
        locations = [line for line in result.stdout.splitlines() if ".loc" in line]
        self.assertEqual(locations, ["  .loc 1 2"] * 4)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source "quoted".c'
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            source.write_text(source_text)
            result = subprocess.run([sys.executable, str(COMPILER), "-o", str(assembly), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            subprocess.run(["gcc", "-Wl,-z,noexecstack", "-o", str(executable), str(assembly)],
                           capture_output=True, text=True, check=True)
            lines = subprocess.run(["readelf", "--debug-dump=decodedline", str(executable)],
                                   capture_output=True, text=True, check=True)
            self.assertIn('source "quoted".c', lines.stdout)
            self.assertIn(" 2 ", lines.stdout)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)

    def test_token_line_numbers(self):
        tokens = tokenize("\nint/*line\nline*/ x; // skip\n\n")
        self.assertEqual([(token.text, token.line_no) for token in tokens],
                         [("int", 2), ("x", 3), (";", 3), ("", 5)])
        with self.assertRaises(CompileError) as caught:
            parse(tokenize("int main(){\n return missing;\n}"))
        self.assertEqual(caught.exception.line_no, 2)
        error = CompileError(3, "lexical error")
        self.assertIsNone(error.line_no)
        result = compile_program("int main(){\n Ω\n}")
        self.assertIn("-:2:  Ω\n", result.stderr)
        self.assertIn("^ invalid token", result.stderr)

    def test_upstream_c_programs(self):
        fixtures = Path(__file__).with_name("test")
        with tempfile.TemporaryDirectory() as directory:
            for source in sorted(fixtures.glob("*.c")):
                with self.subTest(source=source.name):
                    preprocessed = subprocess.run(
                        ["gcc", "-E", "-P", "-C", str(source)],
                        capture_output=True, text=True, check=True)
                    compiled = compile_program(preprocessed.stdout)
                    self.assertEqual(compiled.returncode, 0, compiled.stderr)
                    assembly = Path(directory) / (source.stem + ".s")
                    executable = Path(directory) / source.stem
                    assembly.write_text(compiled.stdout)
                    linked = subprocess.run(
                        ["gcc", "-Wl,-z,noexecstack", "-o", str(executable),
                         str(assembly), "-xc", str(fixtures / "common")],
                        capture_output=True, text=True)
                    self.assertEqual(linked.returncode, 0, linked.stderr)
                    result = subprocess.run([str(executable)], capture_output=True,
                                            text=True, timeout=5)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertTrue(result.stdout.endswith("OK\n"), result.stdout)

    def test_block_scope(self):
        for source, expected in [
            ("int main(){int x=2;{int x=3;}return x;}", 2),
            ("int main(){int x=2;{int x=3;}{int y=4;return x;}}", 2),
            ("int main(){int x=2;{x=3;}return x;}", 3),
            ("int x;int main(){x=7;{int x=3;}return x;}", 7),
            ("int main(){int x=2;return ({int x=3;x;})+x;}", 5),
            ("int f(int x){{int x=3;}return x;}int main(){return f(7);}", 7),
        ]:
            self.assert_program_returns(source, expected)
        for source in ["int main(){{int x=2;}return x;}",
                       "int f(){int x=2;return x;}int main(){return x;}",
                       "int main(){({int x=2;x;});return x;}"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("undefined variable", result.stderr)
        program = parse(tokenize("int main(){int x;{int x;int y;}}"))
        self.assertEqual([var.name for var in program[0].locals], ["y", "x", "x"])

    def test_comments(self):
        for source in ["int main(){/* return 1; */ return 2;}",
                       "int main(){// return 1;\nreturn 2;}"]:
            self.assert_program_returns(source, 2)
        plain = compile_program("int main(){return 42;}")
        commented = compile_program("/*before*/int/*type*/ main(){return/*value*/42;} //after")
        self.assertEqual(commented.returncode, 0, commented.stderr)
        self.assertEqual(commented.stdout, plain.stdout)
        self.assertEqual(tokenize('"// /* */"')[0].str, b"// /* */\0")
        self.assertEqual(tokenize("// eof")[0].kind, "EOF")
        result = compile_program("int main(){\n/* unclosed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("-:2: /* unclosed\n", result.stderr)
        self.assertIn("^ unclosed block comment", result.stderr)

    def test_driver_options(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input file.c"
            output = Path(directory) / "output file.s"
            source.write_text("int main(){return 42;}")
            expected = instruction_assembly(compile_program(source.read_text()).stdout)
            for arguments in [["-o", str(output), str(source)],
                              [str(source), "-o" + str(output)]]:
                result = subprocess.run([sys.executable, str(COMPILER), *arguments],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(instruction_assembly(output.read_text()), expected)
            result = subprocess.run([sys.executable, str(COMPILER), "-o", "-", str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(instruction_assembly(result.stdout), expected)
            result = subprocess.run([sys.executable, str(COMPILER), "-o" + str(output), "-"],
                                    input=source.read_text(), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(instruction_assembly(output.read_text()), expected)
            source.write_text("")
            result = subprocess.run([sys.executable, str(COMPILER), "-o", str(output), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), f'.file 1 "{source}"\n')
            source.write_text("int main(){1=2;}")
            output.write_text("keep")
            result = subprocess.run([sys.executable, str(COMPILER), "-o", str(output), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_text(), "keep")
            result = subprocess.run([sys.executable, str(COMPILER), "-o", directory, "-"],
                                    input="int main(){return 0;}", capture_output=True, text=True)
            self.assertIn("cannot open output file", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("chibicc", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "-o"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("chibicc", result.stderr)

    def test_file_input(self):
        source = "int main(){return 42;}"
        expected = compile_program(source)
        self.assertEqual(expected.returncode, 0, expected.stderr)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source with spaces.c"
            for contents in [source, source + "\n"]:
                path.write_text(contents)
                result = subprocess.run([sys.executable, str(COMPILER), str(path)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(instruction_assembly(result.stdout), instruction_assembly(expected.stdout))
            path.write_text("int main(){\n return missing;\n}\n")
            result = subprocess.run([sys.executable, str(COMPILER), str(path)],
                                    capture_output=True, text=True)
            prefix = f"{path}:2: "
            self.assertEqual(result.stderr, prefix + " return missing;\n"
                             + " " * (len(prefix) + 8) + "^ undefined variable\n")
            path.write_bytes(b"\xff")
            result = subprocess.run([sys.executable, str(COMPILER), str(path)],
                                    capture_output=True, text=True)
            self.assertIn("cannot decode", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "/tmp/chibicc-no-such-source-40.c"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot open", result.stderr)

    def test_statement_expressions(self):
        for body, expected in [
            ("return ({0;});",0), ("return ({0;1;2;});",2),
            ("({0;return 1;2;}); return 3;",1),
            ("return ({1;})+({2;})+({3;});",6),
            ("return ({int x=3;x;});",3),
            ("int x=3; return *({int *p=&x;p;});",3),
            ("return ({char x=7;sizeof(x);});",1),
        ]:
            self.assert_program_returns("int main(){"+body+"}", expected)
        for source in ["int main(){return ({});}", "int main(){return ({int x;});}",
                       "int main(){return ({return 1;});}"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("statement expression returning void", result.stderr)

    def test_hex_string_escapes(self):
        for spelling, expected in [(r"\x00",0),(r"\x77",119),(r"\xA5",165),
                                   (r"\x00ff",255),(r"\x41Z",65),(r"\x1234",52)]:
            self.assert_program_returns('int main(){return "'+spelling+'"[0];}', expected)
        self.assertEqual(tokenize(r'"\x41Z"')[0].str, b"AZ\0")
        self.assertEqual(tokenize(r'"\x00ff"')[0].ty.size, 2)
        for source in [r'int main(){return "\x"[0];}', r'int main(){return "\xg"[0];}']:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("invalid hex escape sequence", result.stderr)

    def test_octal_string_escapes(self):
        for spelling, expected in [(r"\0",0),(r"\20",16),(r"\101",65),
                                   (r"\1500",104),(r"\777",255),(r"\8",56)]:
            self.assert_program_returns('int main(){return "'+spelling+'"[0];}', expected)
        self.assertEqual(tokenize(r'"\1500"')[0].str, b"h0\0")
        self.assertEqual(tokenize(r'"a\0b"')[0].str, b"a\0b\0")
        self.assert_program_returns(r'int main(){return sizeof("a\0b");}', 4)
        self.assert_program_returns(r'int main(){return "\1500"[1];}', 48)

    def test_named_string_escapes(self):
        for escape, expected in [("a",7),("b",8),("t",9),("n",10),("v",11),
                                 ("f",12),("r",13),("e",27),("j",106),("k",107),("l",108)]:
            self.assert_program_returns('int main(){return "\\'+escape+'"[0];}', expected)
        for index, expected in enumerate([7,120,10,121]):
            self.assert_program_returns(r'int main(){return "\ax\ny"['+str(index)+'];}', expected)
        self.assert_program_returns(r'int main(){return "\""[0];}', 34)
        self.assert_program_returns(r'int main(){return "\\"[0];}', 92)
        self.assertEqual(tokenize(r'"\n"')[0].str, b"\n\0")
        self.assertEqual(tokenize(r'"\n"')[0].ty.size, 2)
        self.assertEqual(compile_program('int main(){return "abc\\').returncode, 1)

    def test_string_literals(self):
        for body, expected in [('return ""[0];',0), ('return sizeof("");',1),
                               ('return "abc"[0];',97), ('return "abc"[1];',98),
                               ('return "abc"[2];',99), ('return "abc"[3];',0),
                               ('return sizeof("abc");',4), ('return sizeof("é");',3)]:
            self.assert_program_returns("int main(){"+body+"}", expected)
        token = tokenize('"abc"')[0]
        self.assertEqual(token.str, b"abc\0")
        self.assertEqual(token.ty.size, 4)
        assembly = compile_program('int main(){return "abc"[0];}').stdout
        self.assertIn("  .byte 97\n  .byte 98\n  .byte 99\n  .byte 0\n", assembly)
        self.assertIn("  lea .L..0(%rip), %rax", assembly)
        for source in ['int main(){return "abc;}', 'int main(){return "a\nb"[0];}']:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unclosed string literal", result.stderr)

    def test_char(self):
        for source, expected in [
            ("int main(){char x=1;return x;}",1),
            ("int main(){char x=1;char y=2;return x;}",1),
            ("int main(){char x=1;char y=2;return y;}",2),
            ("int main(){char x;return sizeof(x);}",1),
            ("int main(){char x[10];return sizeof(x);}",10),
            ("int sub_char(char a,char b,char c);int main(){return sub_char(7,3,3);} int sub_char(char a,char b,char c){return a-b-c;}",1),
            ("int main(){char x=255;return x<0;}",1),
            ("int main(){char x=1;int y=513;x=257;return y==513;}",1),
            ("int main(){char a[3];a[1]=7;return a[1];}",7),
            ("char x;int main(){x=255;return x<0;}",1),
            ("int f(char a,char b,char c,char d,char e,char f){return a+2*b+3*c+4*d+5*e+6*f;} int main(){return f(1,2,3,4,5,6);}",91),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(){char x=1;return x;}").stdout
        self.assertIn("  mov %al, (%rdi)\n", assembly)
        self.assertIn("  movsbl (%rax), %eax\n", assembly)

    def test_global_variables(self):
        for source, expected in [
            ("int x; int main(){return x;}",0),
            ("int x; int main(){x=3; return x;}",3),
            ("int x; int y; int main(){x=3; y=4; return x+y;}",7),
            ("int x,y; int main(){x=3; y=4; return x+y;}",7),
            ("int x; int main(){return sizeof(x);}",4),
            ("int x[4]; int main(){return sizeof(x);}",16),
            ("int x; int f(){x=9; return 0;} int main(){f(); return x;}",9),
            ("int x; int main(){int x=3; return x;}",3),
        ]:
            self.assert_program_returns(source, expected)
        for index in range(4):
            self.assert_program_returns("int x[4]; int main(){x[0]=0;x[1]=1;x[2]=2;x[3]=3;"
                                        f"return x[{index}];}}", index)
        assembly = compile_program("int x; int main(){return x;}").stdout
        self.assertIn("  .data\n  .globl x\nx:\n  .zero 4\n", assembly)
        self.assertIn("  lea x(%rip), %rax\n", assembly)
        self.assertEqual(compile_program("int x=3; int main(){return x;}").returncode, 1)
        self.assertEqual(compile_program("int main(){return x;} int x;").returncode, 1)

    def test_unified_objects(self):
        objects = parse(tokenize("int a(){int x;return 3;} int main(){return a();}"))
        self.assertEqual([obj.name for obj in objects], ["main", "a"])
        self.assertTrue(all(obj.is_function and not obj.is_local for obj in objects))
        self.assertTrue(objects[1].locals[0].is_local)
        self.assertEqual(objects[1].ty.kind, "FUNC")
        assembly = CodeGenerator().generate(objects)
        self.assertEqual(assembly.count("  .text\n"), 2)
        self.assert_program_returns("int a(){return 3;} int main(){return a();}", 3)

    def test_sizeof(self):
        for body, expected in [
            ("int x; return sizeof(x);",4), ("int x; return sizeof x;",4),
            ("int *x; return sizeof(x);",8), ("int x[4]; return sizeof(x);",16),
            ("int x[3][4]; return sizeof(x);",48),
            ("int x[3][4]; return sizeof(*x);",16),
            ("int x[3][4]; return sizeof(**x);",4),
            ("int x[3][4]; return sizeof(**x)+1;",5),
            ("int x[3][4]; return sizeof **x+1;",5),
            ("int x[3][4]; return sizeof(**x+1);",4),
            ("int x=1; return sizeof(x=2);",4),
            ("int x=1; sizeof(x=2); return x;",1),
            ("return sizeof missing();",8),
        ]:
            self.assert_program_returns("long missing();int main(){"+body+"}", expected)
        assembly = compile_program("long missing();int main(){return sizeof missing();}").stdout
        self.assertNotIn("call", assembly)
        self.assertEqual(compile_program("int main(){return sizeof *1;}").returncode, 1)
        self.assertEqual(tokenize("sizeof sizeofx")[1].kind, "IDENT")

    def test_subscripts(self):
        for index, expected in [(0,3),(1,4),(2,5)]:
            self.assert_program_returns("int main(){int x[3]; *x=3; x[1]=4; x[2]=5;"
                                        f"return *(x+{index});}}", expected)
        self.assert_program_returns("int main(){int x[3]; *x=3; x[1]=4; 2[x]=5; return *(x+2);}", 5)
        for index in range(6):
            self.assert_program_returns("int main(){int x[2][3]; int *y=x;"
                                        f"y[{index}]={index}; return x[{index//3}][{index%3}];}}", index)
        self.assert_program_returns("int main(){int x[2]; int i=0; x[i=1]=9; return x[i];}", 9)
        a = compile_program("int main(){int x[2]; return x[1];}")
        b = compile_program("int main(){int x[2]; return *(x+1);}")
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(compile_program("int main(){int x[2]; return x[1;}").returncode, 1)

    def test_arrays_of_arrays(self):
        for index, expression in enumerate(["**x", "*(*x+1)", "*(*x+2)",
                                            "**(x+1)", "*(*(x+1)+1)", "*(*(x+1)+2)"]):
            self.assert_program_returns("int main(){int x[2][3]; int *y=x;"
                                        f"*(y+{index})={index}; return {expression};}}", index)
        function = parse(tokenize("int main(){int x[2][3]; return x+1;}"))[0]
        ty = function.locals[0].ty
        self.assertEqual((ty.array_len, ty.size, ty.base.array_len, ty.base.size), (2,24,3,12))
        expression = without_implicit_casts(function.body.body[-1].lhs)
        self.assertEqual(expression.rhs.rhs.value, 12)
        self.assert_program_returns("int main(){int x[2][3][4]; *(*(*(x+1)+2)+3)=9; return *(*(*(x+1)+2)+3);}", 9)

    def test_one_dimensional_arrays(self):
        self.assert_program_returns("int main(){int x[2]; int *y=&x; *y=3; return *x;}", 3)
        for offset, expected in [(0,3),(1,4),(2,5)]:
            self.assert_program_returns("int main(){int x[3]; *x=3; *(x+1)=4; *(x+2)=5;"
                                        f"return *(x+{offset});}}", expected)
        self.assert_program_returns("int main(){int *x[2]; int a=7; *x=&a; return **x;}", 7)
        function = parse(tokenize("int main(){int x[3]; return x;}"))[0]
        assembly = CodeGenerator().generate([function])
        self.assertEqual(function.locals[0].ty.size, 12)
        self.assertEqual(function.locals[0].offset, -12)
        self.assertEqual(function.stack_size, 16)
        self.assertIn("  lea -12(%rbp), %rax\n  jmp .L.return.main", assembly)
        for source in ["int main(){int x[2]; x=3;}", "int main(){int x[a];}",
                       "int main(){int x[2;}"]:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_function_parameters(self):
        for source, expected in [
            ("int add2(int x,int y);int main(){return add2(3,4);} int add2(int x,int y){return x+y;}", 7),
            ("int sub2(int x,int y);int main(){return sub2(4,3);} int sub2(int x,int y){return x-y;}", 1),
            ("int fib(int x);int main(){return fib(9);} int fib(int x){if(x<=1)return 1; return fib(x-1)+fib(x-2);}", 55),
            ("int f(int a,int b,int c,int d,int e,int f){return a+2*b+3*c+4*d+5*e+6*f;} int main(){return f(1,2,3,4,5,6);}", 91),
            ("int set(int *p){*p=9; return *p;} int main(){int x=1; return set(&x);}", 9),
        ]:
            self.assert_program_returns(source, expected)
        function = parse(tokenize("int f(int x,int y){int z; return x-y;}"))[0]
        self.assertEqual([var.name for var in function.params], ["x", "y"])
        self.assertEqual([var.name for var in function.locals], ["z", "x", "y"])
        assembly = CodeGenerator().generate([function])
        self.assertIn("  mov %edi, -8(%rbp)\n  mov %esi, -12(%rbp)\n", assembly)
        self.assertEqual(compile_program("int f(int a,int b,int c,int d,int e,int f,int g){} ").returncode, 1)
        result = compile_program("int f();int main(){return f(*3);}")
        self.assertIn("invalid pointer dereference", result.stderr)

    def test_argument_calls(self):
        helpers = """
int add(int x,int y) {return x+y;} int sub(int x,int y) {return x-y;}
int add6(int a,int b,int c,int d,int e,int f) {return a+b+c+d+e+f;}
"""
        declarations = "int add();int sub();int add6();"
        for source, expected in [
            ('int main(){return add(3,5);}', 8), ('int main(){return sub(5,3);}', 2),
            ('int main(){return add6(1,2,3,4,5,6);}', 21),
            ('int main(){return add6(1,2,add6(3,4,5,6,7,8),9,10,11);}', 66),
            ('int main(){return add6(1,2,add6(3,add6(4,5,6,7,8,9),10,11,12,13),14,15,16);}', 136),
            ('int main(){int x=0; return sub(x=5,x=3);}', 2),
        ]:
            self.assert_program_returns(declarations + source, expected, helpers)
        assembly = compile_program(declarations + 'int main(){return add6(1,2,3,4,5,6);}').stdout
        self.assertIn("  pop %r9\n  pop %r8\n  pop %rcx\n  pop %rdx\n"
                      "  pop %rsi\n  pop %rdi\n", assembly)
        result = compile_program('int f();int main(){return f(1,2,3,4,5,6,7);}')
        self.assertEqual(result.returncode, 1)
        self.assertIn("at most 6 arguments", result.stderr)
        for source in ['int f();int main(){return f(1 2);}', 'int f();int main(){return f(1,);}']:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_zero_argument_calls(self):
        declarations = "int ret3();int ret5();"
        helpers = "int ret3(void) { return 3; } int ret5(void) { return 5; }"
        for source, expected in [('int main(){return ret3();}', 3), ('int main(){return ret5();}', 5),
                                 ('int main(){return ret3()+ret5();}', 8)]:
            self.assert_program_returns(declarations + source, expected, helpers)
        call = parse(tokenize("int ret3();int main(){return ret3();}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.funcname, "ret3")
        self.assertEqual(call.ty.kind, "INT")
        assembly = compile_program(declarations + 'int main(){return ret3();}').stdout
        self.assertIn("  mov $0, %rax\n  call ret3\n", assembly)
        self.assertEqual(compile_program(declarations + 'int main(){return ret3(,);}').returncode, 1)

    def test_pointer_arithmetic(self):
        for source, expected in [
            ('int main(){int x=3; int y=5; return *(1+&x);}', 5),
            ('int main(){int x=3; int y=5; return &y-&x;}', 1),
            ('int main(){int x=3; int y=5; return &x-&y;}', 255),
            ('int main(){int x=3; return (&x+3)-(&x+1);}', 2),
            ('int main(){int x=3; return (&x-2)-&x;}', 254),
            ('int main(){int x=3; int y=5; int *p=&x; return *(p+1);}', 5),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        expression = without_implicit_casts(parse_body("int x; return &x+1;").body.body[-1].lhs.lhs)
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.ty.base.kind, "INT")
        self.assertEqual(expression.rhs.kind, "*")
        self.assertEqual(expression.rhs.rhs.value, 4)
        expression = parse_body("int x,y; return &x-&y;").body.body[-1].lhs.lhs
        self.assertEqual(expression.ty.kind, "INT")
        self.assertEqual(expression.kind, "/")
        self.assertEqual(expression.lhs.ty.kind, "INT")
        self.assertEqual((expression.lhs.kind, expression.rhs.kind), ("CAST", "CAST"))
        self.assertEqual(expression.rhs.lhs.value, 4)
        expression = parse_body("int x; return &x-1+2;").body.body[-1].lhs.lhs
        self.assertEqual(expression.lhs.ty.kind, "PTR")
        expression = without_implicit_casts(parse_body("int x; int *p=&x; return p+1;").body.body[-1].lhs.lhs)
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.rhs.kind, "*")

    def test_address_and_dereference(self):
        for source, expected in [
            ('int main(){ int x=3; return *&x; }', 3),
            ('int main(){ int x=3; int *y=&x; int **z=&y; return **z; }', 3),
            ('int main(){ int x=3; int y=5; return *(&x+1); }', 5),
            ('int main(){ int x=3; int y=5; return *(&y-1); }', 3),
            ('int main(){ int x=3; int *y=&x; *y=5; return x; }', 5),
            ('int main(){ int x=3; int y=5; *(&x+1)=7; return y; }', 7),
            ('int main(){ int x=3; int y=5; *(&y-1)=7; return x; }', 7),
            ('int main(){ int x=1; int *p=&x; int **q=&p; **q=9; return x; }', 9),
            ('int main(){ int x=1; *&x=7; return x; }', 7),
            ('int main(){ int x=3; int *p=&x; return &*p==p; }', 1),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("int *x; 1**x;")
        expression = without_implicit_casts(program.body.body[1].lhs)
        self.assertEqual(expression.kind, "*")
        self.assertEqual(expression.rhs.kind, "DEREF")
        self.assertEqual(expression.rhs.tok.text, "*")
        result = compile_program('int main(){int x; return &x;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -4(%rbp), %rax\n  jmp .L.return.main\n" + EPILOGUE)
        result = compile_program('int main(){int x; return *&x;}')
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -4(%rbp), %rax\n  movsxd (%rax), %rax\n"
                         "  jmp .L.return.main\n" + EPILOGUE)
        for source, position in [('int main(){return &1;}', 19),
                                 ('int main(){return &(1+2);}', 21)]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: "))
                             + "^ not an lvalue\n")

    def test_representative_tokens(self):
        source = 'int main(){return -(1+2)*3>4;}'
        tokens = tokenize(source)
        program = parse(tokens)[0]
        statement = program.body.body[0]
        self.assertIs(program.body.tok, tokens[5])
        self.assertIs(statement.tok, tokens[5])
        comparison = without_implicit_casts(statement.lhs)
        self.assertEqual(comparison.kind, "<")
        self.assertEqual(comparison.tok.text, ">")
        multiply = comparison.rhs
        self.assertEqual(multiply.tok.position, source.index("*"))
        self.assertEqual(multiply.lhs.tok.position, source.index("-"))
        self.assertEqual(multiply.lhs.lhs.tok.position, source.index("+"))
        self.assertEqual(multiply.rhs.tok.text, "3")
        for source, position in [('int main(){1=2;}', 11), ('int main(){(1+2)=3;}', 13),
                                 ('int main(){int a; -a=3;}', 18), ('int main(){(2>1)=3;}', 13)]:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: "))
                                 + "^ not an lvalue\n")
        token = Token("PUNCT", "?", 8)
        for generate, node, message in [
            (CodeGenerator().gen_stmt, Node("UNKNOWN", tok=token), "invalid statement"),
            (CodeGenerator().gen_expr, Node("UNKNOWN", Node("NUM", ty=ty_long), Node("NUM", ty=ty_long),
                                           tok=token), "invalid expression"),
        ]:
            with self.assertRaises(CompileError) as caught:
                generate(node)
            self.assertEqual(caught.exception.position, 8)
            self.assertEqual(str(caught.exception), message)

    def test_while(self):
        for source, expected in [
            ('int main(){int i; i=0; while(i<10) {i=i+1;} return i;}', 10),
            ('int main(){while(0) return 9; return 3;}', 3),
            ('int main(){while(-2) return 7;}', 7),
            ('int main(){int i, sum; i=3; sum=0; while(i) {sum=sum+i; i=i-1;} return sum;}', 6),
            ('int main(){int i, j; i=0; while(i<3) {for(j=0;j<2;j=j+1); i=i+1;} return i+j;}', 5),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("while(1) return 3;")
        node = program.body.body[0]
        self.assertEqual(node.kind, "FOR")
        self.assertIsNone(node.init)
        self.assertIsNone(node.inc)
        expected = CodeGenerator().generate([parse_body("for(;1;) return 3;")])
        self.assertEqual(instruction_assembly(CodeGenerator().generate([program])),
                         instruction_assembly(expected))
        result = compile_program('int main(){while() ;}')
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected an expression", result.stderr)

    def assert_program_returns(self, source, expected, helper_c=""):
        result = compile_program(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            assembly.write_text(result.stdout)
            inputs = [str(assembly)]
            if helper_c:
                helper = Path(directory) / "helper.c"
                helper.write_text(helper_c)
                inputs.append(str(helper))
            linked = subprocess.run(
                ["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), *inputs],
                capture_output=True, text=True,
            )
            self.assertEqual(linked.returncode, 0, linked.stderr)
            executed = subprocess.run([str(executable)], timeout=5)
            self.assertEqual(executed.returncode, expected)

    def test_for(self):
        cases = [
            ('int main(){int i, j;  i=0; j=0; for(i=0;i<=10;i=i+1) j=i+j; return j; }', 55),
            ('int main(){ for(;;) {return 3;} return 5; }', 3),
            ('int main(){int i;  i=4; for(;i<4;i=i+1) return 9; return i; }', 4),
            ('int main(){int i;  i=0; for(;i<3;) i=i+1; return i; }', 3),
            ('int main(){int i;  i=0; for(;;i=i+1) if(i==4) return i; }', 4),
            ('int main(){int sum, i, j;  sum=0; for(i=0;i<3;i=i+1) for(j=0;j<2;j=j+1) sum=sum+1; return sum; }', 6),
            ('int main(){int i;  for(i=0;i<3;i=i+1); return i; }', 3),
            ('int main(){int format;  format=7; return format; }', 7),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("for(;;) return 3;")
        node = program.body.body[0]
        self.assertEqual(without_implicit_casts(node.init), Node("BLOCK"))
        self.assertIsNone(node.cond)
        self.assertIsNone(node.inc)
        self.assertEqual(instruction_assembly(CodeGenerator().generate([program]) + "\n"), PROLOGUE + "  sub $0, %rsp\n"
                         ".L.begin.1:\n  mov $3, %rax\n  jmp .L.return.main\n"
                         "  jmp .L.begin.1\n.L.end.1:\n" + EPILOGUE)
        for source, position, message in [
            ('int main(){for 1;}', 15, "expected '('"),
            ('int main(){for(1 2;3) ;}', 17, "expected ';'"),
            ('int main(){for(;1 2;) ;}', 18, "expected ';'"),
            ('int main(){for(;;1 2) ;}', 19, "expected ')'"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: ")) + "^ " + message + "\n")

    def test_if_tree_and_labels(self):
        program = parse_body("if(1) if(0) return 2; else return 3;")
        outer = program.body.body[0]
        self.assertEqual(outer.kind, "IF")
        self.assertEqual(without_implicit_casts(outer.cond), Node("NUM", value=1))
        self.assertIsNone(outer.els)
        self.assertEqual(without_implicit_casts(outer.then.els), Node("RETURN", lhs=Node("NUM", value=3)))
        assembly = CodeGenerator().generate([program])
        for label in (".L.else.1:", ".L.end.1:", ".L.else.2:", ".L.end.2:"):
            self.assertEqual(assembly.count(label), 1)

    def test_null_statements(self):
        program = parse(tokenize('int main(){ ;;; return 5; }'))[0]
        self.assertEqual(without_implicit_casts(program.body), Node("BLOCK", body=[
            Node("BLOCK"), Node("BLOCK"), Node("BLOCK"),
            Node("RETURN", lhs=Node("NUM", value=5)),
        ]))
        for source in ['int main(){ ;;; return 5; }', 'int main(){ {}; return 5;; }', 'int main(){ return 5; ;;; }']:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n"
                                 "  mov $5, %rax\n  jmp .L.return.main\n" + EPILOGUE)
        # A program containing only null statements does not set a return value.
        result = compile_program('int main(){;;;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

    def test_nested_block_tree(self):
        program = parse(tokenize('int main(){ {1;} return 2; }'))[0]
        self.assertEqual(without_implicit_casts(program.body), Node("BLOCK", body=[
            Node("BLOCK", body=[Node("EXPR_STMT", lhs=Node("NUM", value=1))]),
            Node("RETURN", lhs=Node("NUM", value=2)),
        ]))
        result = compile_program('int main(){ {1;} return 2; }')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n"
                         "  mov $1, %rax\n  mov $2, %rax\n  jmp .L.return.main\n" + EPILOGUE)

    def test_function_definitions(self):
        source = "int ret32();int main(){return ret32();} int ret32(){return 32;}"
        self.assert_program_returns(source, 32)
        self.assert_program_returns("int f(){int x=4; return x;} int main(){int x=3; return f()+x;}", 7)
        assembly = compile_program(source).stdout
        self.assertIn(".L.return.main:", assembly)
        self.assertIn(".L.return.ret32:", assembly)
        self.assertEqual(compile_program("{return 1;}").returncode, 1)
        self.assertEqual(compile_program("int main(){} return 3;").returncode, 1)
        self.assertEqual(compile_program("int main(){return 1}").returncode, 1)
        self.assertEqual(compile_program("").stdout, '.file 1 "-"\n')
        self.assertEqual(parse(tokenize("")), [])

    def test_return_tree(self):
        program = parse_body("return 1+2; 3;")
        self.assertEqual(without_implicit_casts(program.body.body), [
            Node("RETURN", lhs=Node("+", Node("NUM", value=1), Node("NUM", value=2))),
            Node("EXPR_STMT", lhs=Node("NUM", value=3)),
        ])

    def test_local_objects_and_stack_layout(self):
        program = parse_body("int foo=3; int bar=5; return foo+bar;")
        self.assertEqual([var.name for var in program.locals], ["bar", "foo"])
        bar, foo = program.locals
        self.assertIs(program.body.body[0].body[0].lhs.lhs.var, foo)
        expression = without_implicit_casts(program.body.body[2].lhs)
        self.assertIs(expression.lhs.var, foo)
        self.assertIs(program.body.body[1].body[0].lhs.lhs.var, bar)
        self.assertIs(expression.rhs.var, bar)
        CodeGenerator().generate([program])
        self.assertEqual((bar.offset, foo.offset, program.stack_size), (-4, -8, 16))
        another = parse_body("int foo=1; return foo;")
        self.assertIsNot(another.locals[0], foo)
        for source, offsets, size in [
            ("1;", [], 0), ("int x;", [-4], 16),
            ("int a,b,c;", [-4,-8,-12], 16),
            ("int a,b,c,d;", [-4,-8,-12,-16], 16),
        ]:
            program = parse_body(source)
            assembly = CodeGenerator().generate([program])
            self.assertEqual([var.offset for var in program.locals], offsets)
            self.assertEqual(program.stack_size, size)
            self.assertIn(f"  sub ${size}, %rsp\n", assembly)

    def test_statement_list(self):
        statements = parse_body("1; 2+3;")
        self.assertEqual(without_implicit_casts(statements.body.body), [
            Node("EXPR_STMT", lhs=Node("NUM", value=1)),
            Node("EXPR_STMT", lhs=Node("+", Node("NUM", value=2), Node("NUM", value=3))),
        ])
        generator = CodeGenerator()
        generator.generate([statements])
        self.assertEqual(generator.depth, 0)

    def test_empty_program(self):
        # Upstream accepts zero statements but emits no return value.
        # Check the assembly only: the executable's exit status is unspecified.
        for source in ["", " \t\n"]:
            with self.subTest(source=source):
                self.assertEqual(without_implicit_casts(parse_body(source)), Obj("main", body=Node("BLOCK"), is_function=True,
                                                        is_definition=True))
                result = compile_program('int main(){' + source + "}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

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
                self.assertEqual(without_implicit_casts(statements.body.body), [Node("EXPR_STMT", lhs=expected)])
                generator = CodeGenerator()
                generator.generate([statements])
                self.assertEqual(generator.depth, 0)

    def test_exact_assembly(self):
        cases = [
            ("if(1) 2; else 3;", "  mov $1, %rax\n  cmp $0, %rax\n"
             "  je  .L.else.1\n  mov $2, %rax\n  jmp .L.end.1\n"
             ".L.else.1:\n  mov $3, %rax\n.L.end.1:\n"),
            ("if(0) ;", "  mov $0, %rax\n  cmp $0, %rax\n"
             "  je  .L.else.1\n  jmp .L.end.1\n.L.else.1:\n.L.end.1:\n"),
            ("return 3; 42;", "  mov $3, %rax\n  jmp .L.return.main\n  mov $42, %rax\n"),
            ("return 1; return 2;", "  mov $1, %rax\n  jmp .L.return.main\n"
             "  mov $2, %rax\n  jmp .L.return.main\n"),
            ("int a; a=3; a;", "  lea -4(%rbp), %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  mov %eax, (%rdi)\n  lea -4(%rbp), %rax\n  movsxd (%rax), %rax\n"),
            ("int z; z=5;", "  lea -4(%rbp), %rax\n  push %rax\n  mov $5, %rax\n"
             "  pop %rdi\n  mov %eax, (%rdi)\n"),
            ("1; 2; 3;", "  mov $1, %rax\n  mov $2, %rax\n  mov $3, %rax\n"),
            ('42;', "  mov $42, %rax\n"),
            ('5+6*7;', "  mov $7, %rax\n  push %rax\n  mov $6, %rax\n"
             "  pop %rdi\n  imul %edi, %eax\n  push %rax\n  mov $5, %rax\n"
             "  pop %rdi\n  add %edi, %eax\n"),
            ('(3+5)/2;', "  mov $2, %rax\n  push %rax\n  mov $5, %rax\n"
             "  push %rax\n  mov $3, %rax\n  pop %rdi\n  add %edi, %eax\n"
             "  pop %rdi\n  cdq\n  idiv %edi\n"),
            ('10-3;', "  mov $3, %rax\n  push %rax\n  mov $10, %rax\n"
             "  pop %rdi\n  sub %edi, %eax\n"),
            ('-10;', "  mov $10, %rax\n  neg %rax\n"),
            ('+10;', "  mov $10, %rax\n"),
            ('- - +10;', "  mov $10, %rax\n  neg %rax\n  neg %rax\n"),
            ('2*-(3+4);', "  mov $4, %rax\n  push %rax\n  mov $3, %rax\n"
             "  pop %rdi\n  add %edi, %eax\n  neg %rax\n  push %rax\n"
             "  mov $2, %rax\n  pop %rdi\n  imul %edi, %eax\n"),
            ('1==2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  sete %al\n  movzb %al, %rax\n"),
            ('1!=2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  setne %al\n  movzb %al, %rax\n"),
            ('1<2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  setl %al\n  movzb %al, %rax\n"),
            ('1<=2;', "  mov $2, %rax\n  push %rax\n  mov $1, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  setle %al\n  movzb %al, %rax\n"),
            ('1>2;', "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  setl %al\n  movzb %al, %rax\n"),
            ('1>=2;', "  mov $1, %rax\n  push %rax\n  mov $2, %rax\n"
             "  pop %rdi\n  cmp %edi, %eax\n  setle %al\n  movzb %al, %rax\n"),
        ]
        for source, instructions in cases:
            with self.subTest(source=source):
                result = compile_program('int main(){' + source + "}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                stack_size = 16 if source in ("int a; a=3; a;", "int z; z=5;") else 0
                self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + f"  sub ${stack_size}, %rsp\n" + instructions + EPILOGUE)

    def test_executable_exit_status(self):
        # All current upstream examples and earlier arithmetic/control regressions.
        cases = [
            ('int main(){ return 0; }', 0),
            ('int main(){ return 42; }', 42),
            ('int main(){ return 5+20-4; }', 21),
            ('int main(){ return  12 + 34 - 5 ; }', 41),
            ('int main(){ return 5+6*7; }', 47),
            ('int main(){ return 5*(9-6); }', 15),
            ('int main(){ return (3+5)/2; }', 4),
            ('int main(){ return -10+20; }', 10),
            ('int main(){ return - -10; }', 10),
            ('int main(){ return - - +10; }', 10),
            ('int main(){ return 0==1; }', 0),
            ('int main(){ return 42==42; }', 1),
            ('int main(){ return 0!=1; }', 1),
            ('int main(){ return 42!=42; }', 0),
            ('int main(){ return 0<1; }', 1),
            ('int main(){ return 1<1; }', 0),
            ('int main(){ return 2<1; }', 0),
            ('int main(){ return 0<=1; }', 1),
            ('int main(){ return 1<=1; }', 1),
            ('int main(){ return 2<=1; }', 0),
            ('int main(){ return 1>0; }', 1),
            ('int main(){ return 1>1; }', 0),
            ('int main(){ return 1>2; }', 0),
            ('int main(){ return 1>=0; }', 1),
            ('int main(){ return 1>=1; }', 1),
            ('int main(){ return 1>=2; }', 0),
            ('int main(){ int a; a=3; return a; }', 3),
            ('int main(){ int a=3; return a; }', 3),
            ('int main(){ int a=3; int z=5; return a+z; }', 8),
            ('int main(){ int a; int b; a=b=3; return a+b; }', 6),
            ('int main(){ int foo=3; return foo; }', 3),
            ('int main(){ int foo123=3; int bar=5; return foo123+bar; }', 8),
            ('int main(){ return 1; 2; 3; }', 1),
            ('int main(){ 1; return 2; 3; }', 2),
            ('int main(){ 1; 2; return 3; }', 3),
            ('int main(){ {1; {2;} return 3;} }', 3),
            ('int main(){ ;;; return 5; }', 5),
            ('int main(){ if (0) return 2; return 3; }', 3),
            ('int main(){ if (1-1) return 2; return 3; }', 3),
            ('int main(){ if (1) return 2; return 3; }', 2),
            ('int main(){ if (2-1) return 2; return 3; }', 2),
            ('int main(){ if (0) { 1; 2; return 3; } else { return 4; } }', 4),
            ('int main(){ if (1) { 1; 2; return 3; } else { return 4; } }', 3),
            ('int main(){ int i=0; int j=0; for (i=0; i<=10; i=i+1) j=i+j; return j; }', 55),
            ('int main(){ for (;;) return 3; return 5; }', 3),
            ('int main(){ int i=0; while(i<10) i=i+1; return i; }', 10),
            ('int main(){ int i=0; int j=0; while(i<=10) {j=i+j; i=i+1;} return j; }', 55),
            ('int main(){ int x=3; return *&x; }', 3),
            ('int main(){ int x=3; int *y=&x; int **z=&y; return **z; }', 3),
            ('int main(){ int x=3; int y=5; return *(&x+1); }', 5),
            ('int main(){ int x=3; int y=5; return *(&y-1); }', 3),
            ('int main(){ int x=3; int y=5; return *(&x-(-1)); }', 5),
            ('int main(){ int x=3; int *y=&x; *y=5; return x; }', 5),
            ('int main(){ int x=3; int y=5; *(&x+1)=7; return y; }', 7),
            ('int main(){ int x=3; int y=5; *(&y-2+1)=7; return x; }', 7),
            ('int main(){ int x=3; return (&x+2)-&x+3; }', 5),
            ('int main(){ int x, y; x=3; y=5; return x+y; }', 8),
            ('int main(){ int x=3, y=5; return x+y; }', 8),
            ('int main(){if (0) return 2; return 3;}', 3),
            ('int main(){if (1-1) return 2; return 3;}', 3),
            ('int main(){if (1) return 2; return 3;}', 2),
            ('int main(){if (2-1) return 2; return 3;}', 2),
            ('int main(){if (0) {1; 2; return 3;} else {return 4;}}', 4),
            ('int main(){if (1) {1; 2; return 3;} else {return 4;}}', 3),
            ('int main(){if(-3) return 7; else return 9;}', 7),
            ('int main(){if(256) return 7; return 9;}', 7),
            ('int main(){int a; a=0; if(1) a=3; else a=8; return a;}', 3),
            ('int main(){int a; a=0; if(0) a=3; else a=8; return a;}', 8),
            ('int main(){if(1) if(0) return 2; else return 3; return 4;}', 3),
            ('int main(){if(0) if(1) return 2; else return 3; return 4;}', 4),
            ('int main(){if(0) {if(1) return 2;} else return 3;}', 3),
            ('int main(){if(0) return 1; else if(0) return 2; else return 3;}', 3),
            ('int main(){int a; a=0; if(a=5) a=a+2; if(a==7) a=a*2; return a;}', 14),
            ('int main(){if(1); else return 2; return 3;}', 3),
            ('int main(){int ifx, elsewhere; ifx=3; elsewhere=4; if(ifx<elsewhere) return 8; return 9;}', 8),
            ('int main(){;;; return 5;}', 5),
            ('int main(){1;;}', 1),
            ('int main(){int a; a=3;; {;; a=a+2;;}; return a;;}', 5),
            ('int main(){return 7;;;;}', 7),
            ('int main(){{1; {2;} return 3;}}', 3),
            ('int main(){{} return 7;}', 7),
            ('int main(){{{return 5;}} return 9;}', 5),
            ('int main(){int a, b; a=1; {a=4; b=3;} return a+b;}', 7),
            ('int main(){int a; a=2; {a=a*3; {a=a+4;}} return a;}', 10),
            ('int main(){{{{}}} return 8;}', 8),
            ('int main(){return 0;}', 0),
            ('int main(){return 42;}', 42),
            ('int main(){return 5+20-4;}', 21),
            ('int main(){return  12 + 34 - 5 ;}', 41),
            ('int main(){return 5+6*7;}', 47),
            ('int main(){return 5*(9-6);}', 15),
            ('int main(){return (3+5)/2;}', 4),
            ('int main(){return -10+20;}', 10),
            ('int main(){return - -10;}', 10),
            ('int main(){return - - +10;}', 10),
            ('int main(){return 0==1;}', 0),
            ('int main(){return 42==42;}', 1),
            ('int main(){return 0!=1;}', 1),
            ('int main(){return 42!=42;}', 0),
            ('int main(){return 0<1;}', 1),
            ('int main(){return 1<1;}', 0),
            ('int main(){return 2<1;}', 0),
            ('int main(){return 0<=1;}', 1),
            ('int main(){return 1<=1;}', 1),
            ('int main(){return 2<=1;}', 0),
            ('int main(){return 1>0;}', 1),
            ('int main(){return 1>1;}', 0),
            ('int main(){return 1>2;}', 0),
            ('int main(){return 1>=0;}', 1),
            ('int main(){return 1>=1;}', 1),
            ('int main(){return 1>=2;}', 0),
            ('int main(){int a; a=3; return a;}', 3),
            ('int main(){int a, z; a=3; z=5; return a+z;}', 8),
            ('int main(){int a, b; a=b=3; return a+b;}', 6),
            ('int main(){int foo; foo=3; return foo;}', 3),
            ('int main(){int foo123, bar; foo123=3; bar=5; return foo123+bar;}', 8),
            ('int main(){return 1; 2; 3;}', 1),
            ('int main(){1; return 2; 3;}', 2),
            ('int main(){1; 2; return 3;}', 3),
            ('int main(){return 1; return 2;}', 1),
            ('int main(){int foo; foo=7; return (foo+5)*(foo-2); foo=99;}', 60),
            ('int main(){int total; return total=9; total=0;}', 9),
            ('int main(){int returnx, return_, Return; returnx=3; return_=4; Return=5; return returnx+return_+Return;}', 12),
            ('int main(){return(3+4);}', 7),
            ('int main(){return -7;}', 249),
            ('int main(){int foo; foo=3; foo;}', 3),
            ('int main(){int foo123, bar; foo123=3; bar=5; foo123+bar;}', 8),
            ('int main(){int foo, foo123; foo=3; foo123=7; foo+foo123;}', 10),
            ('int main(){int Foo, foo; Foo=3; foo=7; Foo+foo;}', 10),
            ('int main(){int _, _value1; _=2; _value1=5; _+_value1;}', 7),
            ('int main(){int total, left, right; total=left=right=4; total+left+right;}', 12),
            ('int main(){int count; count=3; count=count+4; count;}', 7),
            ('int main(){int alpha, beta, gamma; alpha=1; beta=2; gamma=3; alpha+beta+gamma;}', 6),
            ('int main(){int a; a=3; a;}', 3),
            ('int main(){int a, z; a=3; z=5; a+z;}', 8),
            ('int main(){int a, b; a=b=3; a+b;}', 6),
            ('int main(){int a; a=1; a=a+2; a;}', 3),
            ('int main(){int a, b; a=4; b=7; a=9; b;}', 7),
            ('int main(){int a; a=5==5; a;}', 1),
            ('int main(){int a; a=3; (a=7)+2;}', 9),
            ('int main(){int a, b; a=-(3+4); b=2; a/b;}', 253),
            ('int main(){int a; (a)=6; a;}', 6),
            ('int main(){int a; a=65536*65536; a/65536/65536;}', 0),
            ('int main(){int a, z; a=2; z=8; (a+z)*(z-a); a+z;}', 10),
            ('int main(){1; 2; 3;}', 3),
            ('int main(){42; 0;}', 0),
            ('int main(){1+2; 3*(4+5); (10-3)/2;}', 3),
            ('int main(){5<6; -7;}', 249),
            ('int main(){10;\n 20+22;\n}', 42),
            ('int main(){0;}', 0),
            ('int main(){42;}', 42),
            ('int main(){5+20-4;}', 21),
            ('int main(){ 12 + 34 - 5 ;}', 41),
            ('int main(){5+6*7;}', 47),
            ('int main(){5*(9-6);}', 15),
            ('int main(){(3+5)/2;}', 4),
            ('int main(){255;}', 255),
            ('int main(){256;}', 0),
            ('int main(){ 0042 ;}', 42),
            ('int main(){2147483647;}', 255),
            ('int main(){10-3-2;}', 5),
            ('int main(){0-1;}', 255),
            ('int main(){255+2;}', 1),
            ('int main(){5+ 20-4;}', 21),
            ('int main(){5 +20-4;}', 21),
            ('int main(){\t12\n+\r34\x0b-\x0c5 ;}', 41),
            ('int main(){1\u2003+\u20032;}', 3),
            ('int main(){1+2147483647;}', 0),
            ('int main(){0-2147483647-1;}', 0),
            ('int main(){(5+6)*7;}', 77),
            ('int main(){20/3;}', 6),
            ('int main(){20/2/2;}', 5),
            ('int main(){20/(2/2);}', 20),
            ('int main(){24/3*2;}', 16),
            ('int main(){24/(3*2);}', 4),
            ('int main(){20-3*4+8/2;}', 12),
            ('int main(){((2+3)*(4+(8/2)));}', 40),
            ('int main(){((42));}', 42),
            ('int main(){(0-7)/2;}', 253),
            ('int main(){7/(0-2);}', 253),
            ('int main(){(0-7)/(0-2);}', 3),
            ('int main(){(0-3)*4;}', 244),
            ('int main(){100/(2+3*(4-2));}', 12),
            ('int main(){65536*65536/65536/65536;}', 0),
            ('int main(){-10+20;}', 10),
            ('int main(){- -10;}', 10),
            ('int main(){- - +10;}', 10),
            ('int main(){-1;}', 255),
            ('int main(){+42;}', 42),
            ('int main(){1+-2;}', 255),
            ('int main(){1--2;}', 3),
            ('int main(){1++2;}', 3),
            ('int main(){1 + +2;}', 3),
            ('int main(){-(3+4)*2;}', 242),
            ('int main(){2*-(3+4);}', 242),
            ('int main(){-20/3;}', 250),
            ('int main(){20/-3;}', 250),
            ('int main(){-20/-3;}', 6),
            ('int main(){3*-4+15;}', 3),
            ('int main(){-(-(-5));}', 251),
            ('int main(){-2147483647-1;}', 0),
            ('int main(){0==1;}', 0),
            ('int main(){42==42;}', 1),
            ('int main(){0!=1;}', 1),
            ('int main(){42!=42;}', 0),
            ('int main(){0<1;}', 1),
            ('int main(){1<1;}', 0),
            ('int main(){2<1;}', 0),
            ('int main(){0<=1;}', 1),
            ('int main(){1<=1;}', 1),
            ('int main(){2<=1;}', 0),
            ('int main(){1>0;}', 1),
            ('int main(){1>1;}', 0),
            ('int main(){1>2;}', 0),
            ('int main(){1>=0;}', 1),
            ('int main(){1>=1;}', 1),
            ('int main(){1>=2;}', 0),
            ('int main(){-1<0;}', 1),
            ('int main(){0>-1;}', 1),
            ('int main(){-2<=-1;}', 1),
            ('int main(){-1>=0;}', 0),
            ('int main(){2147483647+1>0;}', 0),
            ('int main(){5+6*7==47;}', 1),
            ('int main(){5+6*7!=47;}', 0),
            ('int main(){5==2+3;}', 1),
            ('int main(){3<4==1;}', 1),
            ('int main(){3==4<5;}', 0),
            ('int main(){1<2<3;}', 1),
            ('int main(){3>2>0;}', 1),
            ('int main(){(3>2)+4;}', 5),
            ('int main(){(5>=5)*7;}', 7),
            ('int main(){1==1==1;}', 1),
            ('int main(){2==2==2;}', 0),
            ('int main(){' + "".join(f"int var{i}={i};" for i in range(30))
             + "+".join(f"var{i}" for i in range(30)) + ";}", 179),
            ('int main(){' + "".join(f"int {chr(97+i)}={i+1};" for i in range(26))
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
                    arguments = ('int main(){' + arguments[0] + "}",)
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
            ("1+9223372036854775808", "1+9223372036854775808\n  ^ integer must fit in a signed 64-bit immediate\n"),
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
                result = compile_program('int main(){' + source + "}")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                if expected.startswith(source + "\n"):
                    expected = 'int main(){' + source + "}\n" + " " * 11 + expected[len(source) + 1:]
                self.assertEqual(result.stderr, "-:1: " + expected.replace("\n", "\n" + " " * len("-:1: "), 1))

    def test_argument_error_has_no_source_location(self):
        for arguments, expected in [((), "no input files\n"),
                                    (("--unknown",), "unknown argument: --unknown\n")]:
            with self.subTest(arguments=arguments):
                result = subprocess.run([sys.executable, str(COMPILER), *arguments],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, expected)

    def test_declarations(self):
        for source, expected in [
            ('int main(){int; return 7;}', 7),
            ('int main(){int x=3,y=x+2; return x+y;}', 8),
            ('int main(){int x=3,*p=&x; *p=7; return x;}', 7),
            ('int main(){int a,b; a=b=3; return a+b;}', 6),
            ('int main(){int integer=5; return integer;}', 5),
            ('int main(){int x=1; {int y=4; return x+y;}}', 5),
            ('int main(){int x=1; {int x=4;} return x;}', 1),
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
        assignment = without_implicit_casts(program.body.body[1].lhs)
        self.assertEqual(assignment.kind, "ASSIGN")
        self.assertEqual(assignment.rhs.kind, "ASSIGN")
        result = compile_program('int main(){int x; return 7;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  mov $7, %rax\n  jmp .L.return.main\n" + EPILOGUE)
        self.assertEqual(tokenize("int integer")[0].kind, "KEYWORD")
        self.assertEqual(tokenize("int integer")[1].kind, "IDENT")

    def test_declaration_errors(self):
        cases = [
            ('int main(){x=3;}', 11, "undefined variable"),
            ('int main(){return x; int x;}', 18, "undefined variable"),
            ('int main(){int x=y;}', 17, "undefined variable"),
            ('int main(){int 3;}', 15, "expected a variable name"),
            ('int main(){int *;}', 16, "expected a variable name"),
            ('int main(){int x y;}', 17, "expected ','"),
            ('int main(){int x,;}', 17, "expected a variable name"),
            ('int main(){int x=;}', 17, "expected an expression"),
            ('int main(){for(int i=0;;);}', 15, "expected an expression"),
            ('int main(){return *1;}', 18, "invalid pointer dereference"),
            ('int main(){int x=3; return *x;}', 27, "invalid pointer dereference"),
            ('int main(){int x,y; return &x+&y;}', 29, "invalid operands"),
            ('int main(){int x; return 1-&x;}', 26, "invalid operands"),
            ('int main(){int x; (x+1)=3;}', 20, "not an lvalue"),
        ]
        for source, position, message in cases:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: "))
                                 + "^ " + message + "\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
