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
    return parse(tokenize('int main(void){' + source + "}"))[0]


def instruction_assembly(assembly):
    """Keep instruction snapshots independent of source-debug metadata."""
    return "".join(line for line in assembly.splitlines(keepends=True)
                   if not line.lstrip().startswith((".file ", ".loc ")))


def grammar_tree(node):
    """Compare syntax trees without generated casts or initialization zeroing."""
    if isinstance(node, list):
        return [grammar_tree(child) for child in node]
    if isinstance(node, Obj):
        return replace(node, body=grammar_tree(node.body))
    if not isinstance(node, Node):
        return node
    if node.kind == "CAST" and node.tok is node.lhs.tok:
        return grammar_tree(node.lhs)
    if node.kind == "COMMA" and node.lhs.kind == "MEMZERO":
        return grammar_tree(node.rhs)
    children = {name: grammar_tree(getattr(node, name))
                for name in ("lhs", "rhs", "cond", "then", "els", "init", "inc", "body", "args")}
    return replace(node, **children)


class ExpressionCompilerTests(unittest.TestCase):
    def test_floating_arithmetic(self):
        for source, expected in [
            ("int main(void){double x=21.5;return x*2-1;}", 42),
            ("int main(void){float x=40.5f;return x+1.5f;}", 42),
            ("int main(void){return 85.0/2;}", 42),
            ("int main(void){return -42.9f;}", 214),
            ("int main(void){double x=0.0/0.0;return x!=x;}", 1),
            ("int main(void){return 0.0/0.0<0.0;}", 0),
            ("int main(void){return sizeof(1f+2)+sizeof(1.0+2);}", 12),
            ("int main(void){return -0.0==0.0;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){float x=3.0f;return -(x*2.0f+1.0f);}").stdout
        for instruction in ("  mulss %xmm1, %xmm0\n", "  addss %xmm1, %xmm0\n", "  xorps %xmm1, %xmm0\n"):
            self.assertIn(instruction, assembly)
        self.assertIn("  and %edi, %eax\n", compile_program("int main(void){return 42&15;}").stdout)
        self.assertIn("  and %rdi, %rax\n", compile_program("int main(void){return 42L&15;}").stdout)

    def test_floating_comparisons(self):
        for source, expected in [
            ("int main(void){return 2.0==2;}", 1),
            ("int main(void){return 5.1f<5;}", 0),
            ("int main(void){return 4.9<=5.0f;}", 1),
            ("double f(void){return 42.0;}int main(void){return f()==42.0;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        for operator, expected in (("==", 0), ("!=", 1), ("<", 0), ("<=", 0)):
            self.assert_program_returns(f"int main(void){{union U{{unsigned long u;double d;}} n={{0x7ff8000000000000}};return n.d{operator}n.d;}}", expected)
        assembly = compile_program("int main(void){return 1.0==1.0;}").stdout
        self.assertIn("  ucomisd %xmm0, %xmm1\n", assembly)
        self.assertIn("  setnp %dl\n  and %dl, %al\n", assembly)
        self.assertIn("  movsd %xmm0, (%rsp)\n", assembly)

    def test_floating_locals_and_casts(self):
        for source, expected in [
            ("int main(void){float x=42.9f;return (int)x;}", 42),
            ("int main(void){double x=42.9;float y=x;return (int)y;}", 42),
            ("int main(void){int x=-42;double y=x;return (int)y;}", 214),
            ("int main(void){unsigned x=0xffffffff;double y=x;return (long)y==4294967295;}", 1),
            ("int main(void){float a[2]={1.0f,42.0f};return (int)a[1];}", 42),
            ("int main(void){return (short)42.9;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){float x=42.9f;return (int)x;}").stdout
        for instruction in ("  movss %xmm0, (%rdi)\n", "  movss (%rax), %xmm0\n", "  cvttss2sil %xmm0, %eax\n"):
            self.assertIn(instruction, assembly)
        self.assertEqual(compile_program("int main(void){long double x;}").returncode, 1)

    def test_floating_literal_bits(self):
        for spelling, kind, value in (("1.5f", "FLOAT", 1.5), (".1E4f", "FLOAT", 1000.0),
                                      ("0x10.1p0", "DOUBLE", 16.0625), ("8f", "FLOAT", 8.0),
                                      ("5.l", "DOUBLE", 5.0)):
            token = tokenize(spelling)[0]
            self.assertEqual((token.ty.kind, token.fvalue), (kind, value))
        helper = '__attribute__((naked)) long bits(void){__asm__("movq %xmm0,%rax\\nret");}'
        self.assert_program_returns("long bits(void);int main(void){1.5;return bits()==4609434218613702656;}", 1, helper)
        self.assert_program_returns("long bits(void);int main(void){1.5f;return bits()==1069547520;}", 1, helper)
        self.assert_program_returns("int main(void){return sizeof(8f)+sizeof(0.0);}", 12)
        assembly = compile_program("int main(void){1.5f;return 42;}").stdout
        self.assertIn("  mov $1069547520, %eax  # float 1.500000\n  movq %rax, %xmm0\n", assembly)

    def test_unnamed_prototype_parameters(self):
        self.assert_program_returns("int f(int,int*);int main(void){int x=20;return f(22,&x);}", 42, "int f(int a,int *b){return a+*b;}")
        function = parse(tokenize("int f(int,char*,int[3]);"))[0]
        self.assertEqual([param.kind for param in function.ty.params], ["INT", "PTR", "PTR"])
        self.assertTrue(all(param.name is None for param in function.ty.params))
        self.assertTrue(all(param.name_pos is not None for param in function.ty.params))
        for source, message in [
            ("int f(int){return 42;}", "parameter name omitted"),
            ("int main(void){int *;}", "variable name omitted"),
            ("typedef int *;", "typedef name omitted"),
            ("int ()();", "function name omitted"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
        self.assertIn("  call f\n", compile_program("int f(int);int main(void){return f(42);}").stdout)

    def test_array_dimension_keywords(self):
        self.assert_program_returns("int f(int a[restrict static 3]){return a[2];}int main(void){int a[3]={1,2,42};return f(a);}", 42)
        function = parse(tokenize("int f(int a[static restrict 3]);"))[0]
        self.assertEqual((function.ty.params[0].kind, function.ty.params[0].base.kind), ("PTR", "INT"))
        assembly = compile_program("int f(int a[restrict static 3]){return a[2];}").stdout
        self.assertIn("  mov %rdi, -8(%rbp)\n", assembly)
        self.assertEqual(compile_program("int f(int a[const 3]);").returncode, 1)

    def test_ignored_qualifiers(self):
        for source in [
            "int main(void){const int x=42;return x;}",
            "int main(void){volatile int x=42;int *const volatile restrict p=&x;return *p;}",
            "int main(void){auto register int x=42;return *(const int *const)&x;}",
            "int main(void){const int x=1;x=42;return x;}",
        ]:
            self.assert_program_returns(source, 42)
        plain = instruction_assembly(compile_program("int main(void){int x=42;return x;}").stdout)
        qualified = instruction_assembly(compile_program("int main(void){const volatile int x=42;return x;}").stdout)
        self.assertEqual(plain, qualified)

    def test_unsigned_constant_expressions(self):
        for source, expected in [
            ("enum{N=(char)255};int main(void){return N==-1;}", 1),
            ("int main(void){char a[1U<-1];return sizeof(a);}", 1),
            ("int main(void){char a[(unsigned long)-1/(1L<<62)+1];return sizeof(a);}", 4),
            ("unsigned long g=(unsigned long)-100/2;int main(void){return g==9223372036854775758UL;}", 1),
            ("unsigned long g=-1UL>>63;int main(void){return g;}", 1),
            ("char g=(char)255;int main(void){return g<0;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        var = parse(tokenize("unsigned long g=-1UL>>63;"))[0]
        self.assertEqual(var.init_data, b"\x01"+b"\x00"*7)
        self.assertIn("g:\n  .byte 1\n", compile_program("unsigned long g=-1UL>>63;int main(void){return g;}").stdout)

    def test_unsigned_pointer_comparisons(self):
        self.assert_program_returns("int main(void){return (void*)0xffffffffffffffff>(void*)0;}", 1)
        self.assert_program_returns("int main(void){return (char*)0<=(char*)0xffffffffffffffff;}", 1)
        self.assert_program_returns("int main(void){return (char*)0-(char*)1<0;}", 1)
        node = parse_body("int x;return &x;").body.body[-1].lhs.lhs
        self.assertTrue(node.ty.is_unsigned)
        self.assertIn("  setb %al\n", compile_program("int main(void){return (void*)0xffffffffffffffff>(void*)0;}").stdout)

    def test_wide_pointer_and_size_expressions(self):
        for source, expected in [
            ("int main(void){return sizeof(sizeof(char));}", 8),
            ("int main(void){return sizeof(_Alignof(int));}", 8),
            ("int main(void){return sizeof(char)<<63>>63;}", 1),
            ("int main(void){return _Alignof(char)<<63>>63;}", 1),
            ("int main(void){return (char*)0x100000000-(char*)0==4294967296;}", 1),
            ("int main(void){return (char*)0-(char*)0x100000000<0;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        node = parse_body("return sizeof(char);").body.body[0].lhs.lhs
        self.assertEqual((node.ty.kind, node.ty.is_unsigned), ("LONG", True))
        assembly = compile_program("int main(void){return sizeof(char)<<63>>63;}").stdout
        self.assertIn("  shr %cl, %rax\n", assembly)

    def test_integer_literal_suffixes(self):
        for spelling, kind, unsigned in (("42", "INT", False), ("42U", "INT", True),
                                        ("42L", "LONG", False), ("42ull", "LONG", True),
                                        ("0xffffffff", "INT", True),
                                        ("0xffffffffffffffff", "LONG", True),
                                        ("18446744073709551615", "LONG", False)):
            token = tokenize(spelling)[0]
            self.assertEqual((token.ty.kind, token.ty.is_unsigned), (kind, unsigned))
        for source, expected in [
            ("int main(void){return sizeof(0L)+sizeof(0U);}", 12),
            ("int main(void){return -1U>>30;}", 3),
            ("int main(void){return 0xffffffffffffffffLL>>63;}", 1),
            ("int main(void){return 18446744073709551615>>63;}", 255),
        ]:
            self.assert_program_returns(source, expected)
        self.assertIn("  shr %cl, %rax\n", compile_program("int main(void){return -1ULL>>63;}").stdout)
        for spelling in ("1lL", "1UU", "1LLL", "1ULx"):
            self.assertEqual(compile_program(f"int main(void){{return {spelling};}}").returncode, 1)

    def test_unsigned_integer_operations(self):
        for source, expected in [
            ("int main(void){unsigned char x=255;return x<0;}", 0),
            ("int main(void){unsigned short x=65535;return (long)x==65535;}", 1),
            ("int main(void){return -1<(unsigned)1;}", 0),
            ("int main(void){return ((unsigned)-1>>1)==2147483647;}", 1),
            ("int main(void){return ((unsigned)-100)/2==2147483598;}", 1),
            ("int main(void){return ((unsigned long)-100)/2==9223372036854775758;}", 1),
            ("int main(void){return ((unsigned)-100)%7;}", 2),
            ("int main(void){return ((long)-1)/(unsigned)100;}", 0),
            ("int main(void){return (long)(unsigned)-1==4294967295;}", 1),
            ("int main(void){return sizeof((unsigned char)1+(unsigned char)1);}", 4),
        ]:
            self.assert_program_returns(source, expected)
        self.assert_program_returns("unsigned char f(void);int main(void){return f();}", 255, "int f(void){return 0x2ff;}")
        assembly = compile_program("int main(void){unsigned x=42;return x/2+(x>>1)+(x<1);}").stdout
        for instruction in ("  div %edi\n", "  shr %cl, %eax\n", "  setb %al\n"):
            self.assertIn(instruction, assembly)
        for spelling in ("signed unsigned", "unsigned void", "unsigned _Bool"):
            self.assertEqual(compile_program(f"int main(void){{{spelling} x;}}").returncode, 1)

    def test_signed_type_specifiers(self):
        for spelling, size in (("signed", 4), ("signed signed", 4), ("signed char signed", 1),
                               ("int short signed", 2), ("signed long long int", 8)):
            self.assert_program_returns(f"int main(void){{return sizeof({spelling});}}", size)
        self.assert_program_returns("int main(void){signed char x=255;return x<0;}", 1)
        self.assertIn("  movsbl (%rax), %eax\n", compile_program("int main(void){signed char x=42;return x;}").stdout)
        for spelling in ("signed void", "signed _Bool", "signed char int"):
            self.assertEqual(compile_program(f"int main(void){{{spelling} x;}}").returncode, 1)

    def test_function_argument_counts(self):
        for source, message in [
            ("int f(int x);int main(void){return f();}", "too few arguments"),
            ("int f(int x);int main(void){return f(1,2);}", "too many arguments"),
            ("int f(void);int main(void){return f(42);}", "too many arguments"),
            ("int f(int x,...);int main(void){return f();}", "too few arguments"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
        self.assert_program_returns("int f();int main(void){return f(42);}", 42, "int f(int x){return x;}")
        function = parse(tokenize("int f(){return 42;}"))[0]
        self.assertTrue(function.ty.is_variadic)
        self.assertIsNotNone(function.va_area)
        self.assertFalse(parse(tokenize("int f(void);"))[0].ty.is_variadic)

    def test_variadic_register_save_area(self):
        prefix = "typedef struct V{int gp_offset;int fp_offset;void *overflow;void *registers;} V;"
        self.assert_program_returns(prefix + "int f(int x,...){V *v=(V*)__va_area__;char *p=v->registers;return *(int*)(p+v->gp_offset);}int main(void){return f(1,42);}", 42)
        self.assert_program_returns(prefix + "int f(int x,int y,...){V *v=(V*)__va_area__;return v->gp_offset;}int main(void){return f(1,2,42);}", 16)
        source = prefix + 'int vsprintf(char *b,char *fmt,V *v);void f(char *b,char *fmt,...){V v=*(V*)__va_area__;vsprintf(b,fmt,&v);}int main(void){char b[20];f(b,"%d",42);return b[0]+b[1];}'
        self.assert_program_returns(source, 102)
        function = next(var for var in parse(tokenize("int f(int x,...){return x;}")) if var.is_function)
        self.assertEqual((function.va_area.name, function.va_area.ty.size), ("__va_area__", 136))
        self.assertEqual(len(function.params), 1)
        assembly = compile_program("int f(int x,...){return x;}").stdout
        self.assertIn("  movl $8,", assembly)
        self.assertIn("  movq %r9,", assembly)
        self.assertIn("  movsd %xmm7,", assembly)

    def test_variadic_function_calls(self):
        helper = "#include <stdarg.h>\nint sum(int n,...){va_list ap;va_start(ap,n);int s=0;for(int i=0;i<n;i++)s+=va_arg(ap,int);va_end(ap);return s;}"
        self.assert_program_returns("int sum(int n,...);int main(void){char a=-1;return sum(3,20,23,a);}", 42, helper)
        self.assert_program_returns('int sprintf(char *buf,char *fmt,...);int main(void){char b[30];sprintf(b,"%d %s",42,"abc");return b[0]+b[1];}', 102)
        ty = parse(tokenize("int sum(int n,...);"))[0].ty
        self.assertTrue(ty.is_variadic)
        self.assertEqual(len(ty.params), 1)
        self.assertEqual(tokenize("...")[0].text, "...")
        assembly = compile_program("int sum(int n,...);int main(void){return sum(1,42);}").stdout
        self.assertIn("  mov $0, %rax\n  call sum\n", assembly)
        self.assertEqual(compile_program("int sum(int n,...,int x);").returncode, 1)

    def test_small_function_return_values(self):
        helper = "int f(void){return 512;}int t(void){return 513;}int c(void){return 0x2ff;}int s(void){return 0x2ffff;}"
        for source, expected in [
            ("_Bool f(void);int main(void){return f();}", 0),
            ("_Bool t(void);int main(void){return t();}", 1),
            ("char c(void);int main(void){return c()<0;}", 1),
            ("short s(void);int main(void){return (long)s()==-1;}", 1),
        ]:
            self.assert_program_returns(source, expected, helper)
        for spelling, instruction in (("_Bool", "movzx %al, %eax"),
                                      ("char", "movsbl %al, %eax"),
                                      ("short", "movswl %ax, %eax")):
            assembly = compile_program(f"{spelling} f(void);int main(void){{return f();}}").stdout
            self.assertIn(f"  call f\n  {instruction}\n", assembly)

    def test_call_stack_alignment(self):
        helper = '__attribute__((naked)) int alignment(void){__asm__("mov %rsp, %rax\\nand $15, %eax\\nret");}'
        for source, expected in [
            ("int alignment(void);int main(void){return alignment();}", 8),
            ("int alignment(void);int main(void){return alignment()+1;}", 9),
            ("int alignment(void);int main(void){int x=alignment();return x;}", 8),
            ("int alignment(void);int sum(int a,int b){return a+b;}int main(void){return sum(alignment(),alignment());}", 16),
        ]:
            self.assert_program_returns(source, expected, helper)
        assembly = compile_program("int alignment(void);int main(void){return alignment()+1;}").stdout
        self.assertIn("  sub $8, %rsp\n  call alignment\n  add $8, %rsp\n", assembly)
        assembly = compile_program("int alignment(void);int main(void){return alignment();}").stdout
        self.assertNotIn("  sub $8, %rsp\n  call alignment", assembly)

    def test_do_while_loops(self):
        for source, expected in [
            ("int main(void){int x=0;do{x=42;}while(0);return x;}", 42),
            ("int main(void){int x=40;do{++x;}while(x<42);return x;}", 42),
            ("int main(void){int x=0;do{++x;continue;x=100;}while(x<42);return x;}", 42),
            ("int main(void){int x=42;do{break;x=1;}while(1);return x;}", 42),
            ("int main(void){int x=0;do{do{break;}while(1);++x;}while(x<42);return x;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){do{}while(0);return 42;}").stdout
        self.assertIn("  jne .L.begin.1\n", assembly)
        self.assertEqual(compile_program("int main(void){do{}while(0)return 42;}").returncode, 1)

    def test_static_global_variables(self):
        source = "static int g=42;int main(void){return g;}"
        self.assert_program_returns(source, 42, "int g=1;")
        assembly = compile_program(source).stdout
        self.assertIn("  .local g\n", assembly)
        self.assertNotIn("  .globl g\n", assembly)
        program = parse(tokenize('char *p="abc";static int g;int h;'))
        self.assertEqual({var.name: var.is_static for var in program if not var.name.startswith(".L")}, {"p": False, "g": True, "h": False})
        self.assertTrue(next(var for var in program if var.name.startswith(".L")).is_static)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "test.s").write_text(assembly)
            subprocess.run(["gcc", "-c", str(path / "test.s"), "-o", str(path / "test.o")], check=True, capture_output=True)
            symbols = subprocess.run(["nm", str(path / "test.o")], check=True, capture_output=True, text=True).stdout
            self.assertRegex(symbols, r"(?m)^\w+ d g$")

    def test_return_without_value(self):
        self.assert_program_returns("int g;void f(void){g=42;return;g=1;}int main(void){f();return g;}", 42)
        function = next(var for var in parse(tokenize("void f(void){return;}")) if var.is_function)
        self.assertIsNone(function.body.body[0].lhs)
        assembly = compile_program("void f(void){return;}").stdout
        self.assertIn("  jmp .L.return.f\n", assembly)
        self.assertNotIn("  mov $", assembly)

    def test_compound_literals(self):
        for source, expected in [
            ("int main(void){return (int){42};}", 42),
            ("int main(void){return ((int[]){1,2,42})[2];}", 42),
            ("int main(void){return ((struct T{char a;int b;}){1,42}).b;}", 42),
            ("int main(void){int x=42;return (int){x};}", 42),
            ("int main(void){int *p=&(int){1};*p=42;return *p;}", 42),
            ("int *p=&(int){42};int main(void){return *p;}", 42),
            ("struct T{int x;struct T *next;};struct T *p=&(struct T){1,&(struct T){42,0}};int main(void){return p->next->x;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        self.assertIn("  rep stosb\n", compile_program("int main(void){return (int){42};}").stdout)
        assembly = compile_program("int *p=&(int){42};int main(void){return *p;}").stdout
        self.assertIn("  .quad .L..0+0\n", assembly)
        self.assertNotIn("  rep stosb\n", assembly)

    def test_static_local_variables(self):
        for source, expected in [
            ("int f(void){static int x=40;return ++x;}int main(void){f();return f();}", 42),
            ("int f(void){static int x;return ++x;}int main(void){f();return f();}", 2),
            ("int f(void){static int x=20;return ++x;}int h(void){static int x=20;return ++x;}int main(void){int a=f();int b=h();return a+b;}", 42),
            ("int main(void){static int a[]={1,42};return a[1];}", 42),
        ]:
            self.assert_program_returns(source, expected)
        program = parse(tokenize("int f(void){static int x=42;return x;}"))
        function = next(var for var in program if var.is_function)
        self.assertEqual(function.locals, [])
        assembly = compile_program("int f(void){static int x=42;return x;}").stdout
        self.assertIn("  .data\n.L..0:\n  .byte 42\n", assembly)
        self.assertNotIn("  rep stosb\n", assembly)
        result = compile_program("int g(void);int main(void){static int x=g();return x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a compile-time constant", result.stderr)

    def test_alignof_expressions(self):
        for source, expected in [
            ("int main(void){char x;return _Alignof(x);}", 1),
            ("int main(void){int x;return _Alignof x;}", 4),
            ("int main(void){int x=0;int y=_Alignof(++x);return x+y;}", 4),
            ("int main(void){_Alignas(32) int x;return _Alignof(x);}", 4),
            ("int f(void);int main(void){return _Alignof f();}", 4),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int f(void);int main(void){return _Alignof f();}").stdout
        self.assertNotIn("  call f\n", assembly)
        self.assertIn("  mov $4, %rax\n", assembly)

    def test_alignof_and_alignas(self):
        for source, expected in [
            ("int main(void){return _Alignof(int);}", 4),
            ("int main(void){_Alignas(32) char x,y;return &y-&x;}", 32),
            ("int main(void){_Alignas(long) char x,y;return &y-&x;}", 8),
            ("int main(void){struct T{_Alignas(16) char x,y;} v;return &v.y-&v.x;}", 16),
            ("int main(void){return _Alignof(union T{_Alignas(16) char x;int y;});}", 16),
            ("int main(void){_Alignas(32) int x;return _Alignof(int);}", 4),
        ]:
            self.assert_program_returns(source, expected)
        var = parse(tokenize("_Alignas(32) int g;"))[0]
        self.assertEqual((var.align, var.ty.align), (32, 4))
        self.assertIn("  .align 32\n", compile_program("_Alignas(32) int g;int main(void){return 0;}").stdout)
        result = compile_program("int f(_Alignas(32) int x);")
        self.assertEqual(result.returncode, 1)
        self.assertIn("_Alignas is not allowed", result.stderr)

    def test_block_extern_declarations(self):
        source = "int main(void){extern int g;int f(int x);extern int h(int x);return f(g)+h(21);}"
        self.assert_program_returns(source, 42, "int g=21;int f(int x){return x;}int h(int x){return x;}")
        self.assert_program_returns("int main(void){int g=42;{extern int g;g=1;}return g;}", 42, "int g=0;")
        function = next(var for var in parse(tokenize(source)) if var.name == "main")
        self.assertEqual(function.locals, [])
        assembly = compile_program(source).stdout
        self.assertNotIn("g:\n", assembly)
        self.assertIn("  call f\n", assembly)
        result = compile_program("int main(void){{int f(int x);}return f(42);}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("implicit declaration", result.stderr)

    def test_extern_global_declarations(self):
        source = "extern int g;extern int *p;int main(void){return g+*p;}"
        self.assert_program_returns(source, 42, "int g=21;int *p=&g;")
        assembly = compile_program(source).stdout
        self.assertNotIn("g:\n", assembly)
        self.assertNotIn("p:\n", assembly)
        self.assertIn("  lea g(%rip), %rax\n", assembly)
        objects = parse(tokenize("extern int g;int x;int f(void);"))
        self.assertEqual({var.name: var.is_definition for var in objects}, {"g": False, "x": True, "f": False})
        self.assert_program_returns("typedef static int T;int main(void){T x=42;return x;}", 42)

    def test_global_alignment_directives(self):
        for source in [
            "long g;char pad;int main(void){return (long)&g%8;}",
            "long g=42;char pad=1;int main(void){return (long)&g%8;}",
        ]:
            self.assert_program_returns(source, 0)
        assembly = compile_program("char c;short s;int i;long l;int main(void){return 0;}").stdout
        for name, alignment in (("c", 1), ("s", 2), ("i", 4), ("l", 8)):
            self.assertIn(f"  .globl {name}\n  .align {alignment}\n", assembly)

    def test_void_parameter_lists(self):
        self.assert_program_returns("int f(void);int f(void){return 42;}int main(void){return f();}", 42)
        function = next(var for var in parse(tokenize("int f(void){return 42;}")) if var.is_function)
        self.assertEqual(function.ty.params, [])
        self.assertEqual(function.params, [])
        assembly = compile_program("int f(void){return 42;}int main(void){return f();}").stdout
        self.assertIn("  call f\n", assembly)
        self.assertEqual(compile_program("int f(void int x);int main(void){return 0;}").returncode, 1)

    def test_flexible_array_member_initializers(self):
        for source, expected in [
            ("int main(void){struct T{int a;int b[];} x={1,{2,42}};return x.b[1];}", 42),
            ("int main(void){struct T{int a;int b[];} x={1,2,42};return sizeof(x);}", 12),
            ('struct T{char a;char b[];} g={1,"abc"};int main(void){return g.b[2];}', 99),
            ("typedef struct T{char a;char b[];} T;T x={1,2,3};T y={1,2,3,4,5};int main(void){return sizeof(x)+sizeof(y)+sizeof(T);}", 9),
        ]:
            self.assert_program_returns(source, expected)
        program = parse(tokenize("struct T{int a;int b[];} x={1,2,42};struct T y;"))
        x = next(var for var in program if var.name == "x")
        y = next(var for var in program if var.name == "y")
        self.assertEqual((x.ty.size, y.ty.size), (12, 4))
        self.assertIsNot(x.ty.members[-1], y.ty.members[-1])
        self.assertEqual(x.init_data[-4:], b"\x2a\x00\x00\x00")

    def test_flexible_array_member_size(self):
        for source, expected in [
            ("int main(void){return sizeof(struct T{int x;int y[];});}", 4),
            ("int main(void){return sizeof(struct T{char x;long y[];});}", 8),
            ("int main(void){struct T{int x;int y[];} v;return sizeof(v.y);}", 0),
            ("int main(void){struct T{int x;int y[];} v;char *p=&v;char *q=v.y;return q-p;}", 4),
        ]:
            self.assert_program_returns(source, expected)
        var = parse(tokenize("struct T{int x;int y[];} g;"))[0]
        self.assertEqual((var.ty.size, var.ty.members[-1].ty.array_len), (4, 0))
        self.assertIn("g:\n  .zero 4\n", compile_program("struct T{int x;int y[];} g;int main(void){return sizeof(g);}").stdout)

    def test_uninitialized_globals_in_bss(self):
        source = "int a;int b=0;char c[8];int main(void){return a+b+c[7];}"
        self.assert_program_returns(source, 0)
        assembly = compile_program(source).stdout
        self.assertIn("  .globl a\n  .align 4\n  .bss\na:\n  .zero 4\n", assembly)
        self.assertIn("  .globl b\n  .align 4\n  .data\nb:\n  .byte 0\n", assembly)
        self.assertIn("  .globl c\n  .align 1\n  .bss\nc:\n  .zero 8\n", assembly)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "test.s").write_text(assembly)
            subprocess.run(["gcc", "-c", str(path / "test.s"), "-o", str(path / "test.o")], check=True, capture_output=True)
            symbols = subprocess.run(["nm", str(path / "test.o")], check=True, capture_output=True, text=True).stdout
            self.assertRegex(symbols, r"(?m)^\w+ B a$")
            self.assertRegex(symbols, r"(?m)^\w+ D b$")

    def test_trailing_initializer_commas(self):
        for source, expected in [
            ("int main(void){int a[]={1,2,42,};return a[2];}", 42),
            ("int main(void){struct T{int a,b;} x={1,42,};return x.b;}", 42),
            ("int main(void){union T{int a;char b;} x={42,};return x.a;}", 42),
            ("enum T{A,B=42,};int main(void){return B;}", 42),
            ("int main(void){int a[2][2]={42,};return a[0][0]+a[1][1];}", 42),
            ("struct T{int a,b;} g[]={1,2,3,42,};int main(void){return g[1].b;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        self.assertIn("  mov $12, %rcx\n", compile_program("int main(void){int a[]={1,2,42,};return a[2];}").stdout)
        self.assertEqual(compile_program("int main(void){int x={42,};}").returncode, 1)

    def test_scalar_initializer_braces(self):
        for source in [
            "int main(void){int x={42};return x;}",
            "int main(void){int x={{{42}}};return x;}",
            "int x={{42}};int main(void){return x;}",
            "int main(void){int a[2]={{1},{{42}}};return a[1];}",
            "int g=42;int *p={&g};int main(void){return *p;}",
        ]:
            self.assert_program_returns(source, 42)
        self.assertIn("  mov $42, %rax\n", compile_program("int main(void){int x={42};return x;}").stdout)
        for source in ("int main(void){int x={};}", "int main(void){int x={1,2};}"):
            self.assertEqual(compile_program(source).returncode, 1)

    def test_omitted_initializer_braces(self):
        for source, expected in [
            ("int main(void){int a[2][2]={1,2,3,42};return a[1][1];}", 42),
            ("int main(void){struct T{int a,b;} v[2]={1,2,3,42};return v[1].b;}", 42),
            ("struct T{int a[2];} g[2]={{1,2},3,42};int main(void){return g[1].a[1];}", 42),
            ("int main(void){union T{int a;long b;} x=42;return x.a;}", 42),
            ("int main(void){int a[2][2]={42};return a[0][0]+a[1][1];}", 42),
            ('char g[][4]={97,98,99,0,100,101,102,0};int main(void){return sizeof(g)+g[1][2];}', 110),
        ]:
            self.assert_program_returns(source, expected)
        self.assertIn("  mov $16, %rcx\n", compile_program("int main(void){int a[2][2]={1,2,3,42};return a[1][1];}").stdout)

    def test_global_address_initializers(self):
        for source, expected in [
            ("int g=42;int *p=&g;int main(void){return *p;}", 42),
            ("int g[2]={1,42};int *p=g+1;int main(void){return *p;}", 42),
            ("int g[2]={42,1};int *p=g-1;int main(void){return p[1];}", 42),
            ("struct T{char a;int b;} g={1,42};int *p=&g.b;int main(void){return *p;}", 42),
            ("struct T{int a[2];} g={{1,42}};int *p=g.a;int main(void){return p[1];}", 42),
            ("int g=42;int *p[2]={&g,&g};int main(void){return *p[1];}", 42),
            ("union T{int a;char b[8];} g={42};int main(void){return g.a;}", 42),
            ('char *p="abc"+1;int main(void){return p[0];}', 98),
            ("int g=42;int *p=1?&g:0;int main(void){return *p;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        program = parse(tokenize("int g[2];int *p=g+1;"))
        pointer = next(var for var in program if var.name == "p")
        self.assertEqual([(rel.offset, rel.label, rel.addend) for rel in pointer.relocations], [(0, "g", 4)])
        self.assertIn("  .quad g+4\n", compile_program("int g[2];int *p=g+1;int main(void){return 0;}").stdout)
        result = compile_program("int g=42;int x=g;int main(void){return x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid initializer", result.stderr)

    def test_global_struct_initializers(self):
        for source, expected in [
            ("struct T{char a;int b;} g={1,42};int main(void){return g.b;}", 42),
            ("struct T{int a[2];} g[2]={{{1,42}}};int main(void){return g[0].a[1]+g[1].a[0];}", 42),
            ("struct T{int a,b;} g={42};int main(void){return g.a+g.b;}", 42),
            ("struct T{struct U{int n;} u;} g={{42}};int main(void){return g.u.n;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        var = parse(tokenize("struct T{char a;int b;} g={1,42};"))[0]
        self.assertEqual(var.init_data, b"\x01\x00\x00\x00\x2a\x00\x00\x00")
        self.assertIn("g:\n  .byte 1\n  .byte 0\n", compile_program("struct T{char a;int b;} g={1,42};int main(void){return g.b;}").stdout)

    def test_global_scalar_initializers(self):
        for source, expected in [
            ("char a=1;short b=2;int c=3;long d=36;int main(void){return a+b+c+d;}", 42),
            ("int x=6*7;int main(void){return x;}", 42),
            ('char s[]="abc";int main(void){return s[2];}', 99),
            ("int a[]={1,2,42};int main(void){return a[2];}", 42),
            ("int a[3]={42};int main(void){return a[0]+a[2];}", 42),
            ("char x=-1;short y=-2;int main(void){return x+y+45;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        var = parse(tokenize("int x=0x01020304;"))[0]
        self.assertEqual(var.init_data, b"\x04\x03\x02\x01")
        assembly = compile_program("int x=0x01020304;int main(void){return x;}").stdout
        self.assertIn("x:\n  .byte 4\n  .byte 3\n  .byte 2\n  .byte 1\n", assembly)
        result = compile_program("int f();int x=f();int main(void){return x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not a compile-time constant", result.stderr)

    def test_union_initializers(self):
        for source, expected in [
            ("int main(void){union T{int a;char b[4];} x={0x01020304};return x.b[0];}", 4),
            ("int main(void){union T{int a;char b[4];} x={0x01020304};return x.b[1];}", 3),
            ("int main(void){union T{struct S{char a,b,c,d;} s;int n;} x={{4,3,2,1}};return x.n==0x01020304;}", 1),
            ("int main(void){union T{char a;long b;} x={42};return x.a;}", 42),
            ("int main(void){union T{char a;long b;} x={42};char *p=&x;return p[7];}", 0),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){union T{char a;long b;} x={42};return x.a;}").stdout
        self.assertIn("  mov $8, %rcx\n", assembly)
        self.assertIn("  mov %al, (%rdi)\n", assembly)
        for source in ("int main(void){union T{int a,b;} x={1,2};}",
                       "int main(void){union T{int a;} x={};}"):
            self.assertEqual(compile_program(source).returncode, 1)

    def test_struct_copy_initializers(self):
        for source in [
            "int main(void){struct T{int a,b;} x={1,42};struct T y=x;return y.b;}",
            "int main(void){struct T{int a;} x={42};struct T y=(x);return y.a;}",
            "int main(void){struct T{int a;} x={42};struct U{struct T t;} u={x};return u.t.a;}",
            "int main(void){struct T{char a[9];} x={};x.a[8]=42;struct T y=x;return y.a[8];}",
        ]:
            self.assert_program_returns(source, 42)
        assembly = compile_program("int main(void){struct T{int a;} x={42};struct T y=x;return y.a;}").stdout
        self.assertIn("  mov 3(%rax), %r8b\n  mov %r8b, 3(%rdi)\n", assembly)

    def test_struct_initializers(self):
        for source, expected in [
            ("int main(void){struct T{char a;int b;} x={1,42};return x.b;}", 42),
            ("int main(void){struct T{int a,b,c;} x={42};return x.a+x.b+x.c;}", 42),
            ("int main(void){struct T{int a,b;} x={};return x.a+x.b;}", 0),
            ("int main(void){struct T{int a[2];struct U{int x;} b;} v={{1,2},{42}};return v.b.x;}", 42),
            ("int main(void){struct T{int a,b;} v[]={{1,2},{3,42}};return v[1].b;}", 42),
            ("int main(void){struct T{char a;int b;} x={1};char *p=&x;return p[1]+p[2]+p[3];}", 0),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("struct T{char a;int b;} x={1,42};")
        self.assertEqual([member.idx for member in function.locals[0].ty.members], [0, 1])
        self.assertIn("  add $4, %rax\n", compile_program("int main(void){struct T{char a;int b;} x={1,42};return x.b;}").stdout)

    def test_deduced_array_lengths(self):
        for source, expected in [
            ("int main(void){int a[]={1,2,42};return a[2];}", 42),
            ("int main(void){int a[]={1,2,3};return sizeof(a);}", 12),
            ('int main(void){char s[]="abc";return sizeof(s);}', 4),
            ('typedef char T[];int main(void){T a="abc";T b="x";return sizeof(a)+sizeof(b);}', 6),
            ("int main(void){int a[][2]={{1,2},{3,42}};return a[1][1];}", 42),
            ("int main(void){int i=0;int a[]={++i,++i};return i+a[0]+a[1];}", 5),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("int a[]={1,2,3};")
        self.assertEqual((function.locals[0].ty.array_len, function.locals[0].ty.size), (3, 12))
        self.assertIn("  mov $12, %rcx\n", compile_program("int main(void){int a[]={1,2,3};return sizeof(a);}").stdout)
        result = compile_program("int main(void){int a[];}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("variable has incomplete type", result.stderr)

    def test_string_initializers(self):
        for source, expected in [
            ('int main(void){char a[4]="abc";return a[2];}', 99),
            ('int main(void){char a[4]="abc";return a[3];}', 0),
            ('int main(void){char a[7]="abc";return a[6];}', 0),
            ('int main(void){char a[2]="abc";return a[1];}', 98),
            ('int main(void){char a[2][4]={"abc","def"};return a[1][2];}', 102),
            (r'int main(void){char a[2]="\x80";return a[0]<0;}', 1),
            (r'int main(void){int a[2]="\x80";return a[0]<0;}', 1),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program('int main(void){char a[4]="abc";return a[0];}').stdout
        self.assertIn("  mov $97, %rax\n", assembly)
        self.assertIn("  mov %al, (%rdi)\n", assembly)
        self.assertNotIn("  .data\n", assembly)

    def test_excess_initializer_elements(self):
        for source, expected in [
            ("int main(void){int a[1]={42,3,4};return a[0];}", 42),
            ("int main(void){int i=0;int a[1]={42,++i};return a[0]+i;}", 42),
            ("int main(void){int a[1]={42,{{3}}};return a[0];}", 42),
            ("int main(void){int a[1][1]={{42,3},{4}};return a[0][0];}", 42),
            ("int f();int main(void){int a[1]={42,f()};return a[0];}", 42),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int f();int main(void){int a[1]={42,f()};return a[0];}").stdout
        self.assertNotIn("  call f\n", assembly)
        for source in ("int main(void){int a[1]={42,missing};}",
                       "int main(void){int a[1]={42,{3,4}};}"):
            self.assertEqual(compile_program(source).returncode, 1)

    def test_partial_array_initializers(self):
        for source, expected in [
            ("int main(void){int a[3]={42};return a[0]+a[1]+a[2];}", 42),
            ("int main(void){int a[3]={};return a[0]+a[1]+a[2];}", 0),
            ("int main(void){int a[2][3]={{1,2}};return a[0][1]+a[1][0]+a[1][2];}", 2),
            ("int main(void){int x=42;char a[7]={};return x+a[6];}", 42),
            ("int main(void){int a[2]={a[1]+42};return a[0];}", 42),
        ]:
            self.assert_program_returns(source, expected)
        expression = parse_body("int a[3]={42};").body.body[0].body[0].lhs
        self.assertEqual((expression.kind, expression.lhs.kind), ("COMMA", "MEMZERO"))
        self.assertEqual(expression.lhs.var.ty.size, 12)
        assembly = compile_program("int main(void){int a[3]={42};return a[2];}").stdout
        self.assertIn("  mov $12, %rcx\n", assembly)
        self.assertIn("  mov $0, %al\n  rep stosb\n", assembly)
        self.assertLess(assembly.index("  rep stosb\n"), assembly.index("  mov $42, %rax\n"))

    def test_local_array_initializers(self):
        for source, expected in [
            ("int main(void){int a[3]={1,2,42};return a[2];}", 42),
            ("int main(void){int a[2][3]={{1,2,3},{4,5,42}};return a[1][2];}", 42),
            ("int main(void){int i=0;int a[3]={++i,++i,++i};return a[0]+2*a[1]+3*a[2];}", 14),
            ("int main(void){char a[2]={255,42};return a[0]<0;}", 1),
            ("int main(void){int x=42;int *a[1]={&x};return *a[0];}", 42),
        ]:
            self.assert_program_returns(source, expected)
        node = grammar_tree(parse_body("int a[2]={3,4};").body.body[0].body[0].lhs)
        self.assertEqual((node.kind, node.lhs.kind, node.lhs.lhs.kind), ("COMMA", "COMMA", "NULL_EXPR"))
        self.assertEqual((node.lhs.rhs.kind, node.rhs.kind), ("ASSIGN", "ASSIGN"))
        assembly = compile_program("int main(void){int a[2]={3,4};return a[1];}").stdout
        self.assertIn("  mov %eax, (%rdi)\n", assembly)
        self.assert_program_returns("int main(void){int a[1]={1,};return a[0];}", 1)

    def test_constant_expressions(self):
        for source, expected in [
            ("enum{N=3*2};int main(void){char a[N+1];return sizeof(a);}", 7),
            ("enum{N=-1};int main(void){switch(N){case -1:return 42;}return 1;}", 42),
            ("enum{N=(long)-17/6};int main(void){return N==-2;}", 1),
            ("enum{N=(long)-17%6};int main(void){return N==-5;}", 1),
            ("enum{N=(long)9007199254740993/3-3002399751580331};int main(void){return N;}", 0),
            ("int main(void){char a[1?3:1/0];return sizeof(a);}", 3),
            ("int main(void){char a[(int)0xfffffffffff+5];return sizeof(a);}", 4),
            ("enum{N=(char)255};int main(void){return N==-1;}", 1),
            ("enum{N=(_Bool)256};int main(void){return N;}", 0),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("enum{N=3*2};int main(void){char a[N+1];return sizeof(a);}").stdout
        self.assertIn("  mov $7, %rax\n", assembly)
        self.assertNotIn("  imul ", assembly)
        for source, message in [
            ("int main(void){int n=3;int a[n];}", "not a compile-time constant"),
            ("int f();enum{N=f()};", "not a compile-time constant"),
            ("enum{N=1/0};", "division by zero in constant expression"),
            ("enum{N=1<<64};", "invalid shift count in constant expression"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_conditional_operator(self):
        for source, expected in [
            ("int main(void){return 0?3:42;}", 42),
            ("int main(void){return 1?42:3;}", 42),
            ("int main(void){return 0?1:0?2:42;}", 42),
            ("int main(void){return 1?1,42:3;}", 42),
            ("int main(void){int x=0;int y=1?++x:++x;return y+x;}", 2),
            ("int main(void){int *p=0;return p?*p:42;}", 42),
            ("int main(void){return (1?-1:(long)0)<0;}", 1),
            ("int main(void){return sizeof(1?2:(long)3);}", 8),
            ("int main(void){int x=0;1?(void)(x=42):(void)(x=3);return x;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        node = grammar_tree(parse_body("return 0?1:0?2:3;").body.body[0].lhs)
        self.assertEqual((node.kind, node.els.kind), ("COND", "COND"))
        assembly = compile_program("int main(void){return 1?42:0;}").stdout
        self.assertIn("  je .L.else.1\n", assembly)
        self.assertIn(".L.end.1:\n", assembly)
        self.assertEqual(compile_program("int main(void){return 1?2;}").returncode, 1)

    def test_shift_operators(self):
        for source, expected in [
            ("int main(void){return 1<<2+1;}", 8),
            ("int main(void){return 16>>1>>1;}", 4),
            ("int main(void){return -8>>1;}", 252),
            ("int main(void){return 1<<3<9;}", 1),
            ("int main(void){long x=1;x<<=32;return x>>32;}", 1),
            ("int main(void){int a[1];a[0]=3;int i=0;a[i++]<<=1;return i+a[0];}", 7),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual([token.text for token in tokenize("<<= >>= << >>")[:-1]], ["<<=", ">>=", "<<", ">>"])
        for spelling, register in (("int", "%eax"), ("long", "%rax")):
            assembly = compile_program(f"int main(void){{{spelling} x=-8;return x>>1;}}").stdout
            self.assertIn(f"  mov %rdi, %rcx\n  sar %cl, {register}\n", assembly)
        node = parse_body("return (char)1<<1;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.ty.kind), ("<<", "CHAR"))

    def test_switch_cases(self):
        for source, expected in [
            ("int main(void){switch(1){case 0:return 3;case 1:return 42;}return 7;}", 42),
            ("int main(void){int x=0;switch(1){case 1:x=3;case 2:x+=4;}return x;}", 7),
            ("int main(void){switch(3){case 1:return 7;default:return 42;}}", 42),
            ("int main(void){switch(3){case 1:return 7;}return 42;}", 42),
            ("int main(void){switch(-1){case 0xffffffff:return 42;}return 1;}", 42),
            ("int main(void){switch(1){case 1:switch(2){case 2:break;}return 42;}return 1;}", 42),
            ("int main(void){int x=0;for(int i=0;i<3;i++){switch(i){case 1:continue;default:x++;}}return x;}", 2),
        ]:
            self.assert_program_returns(source, expected)
        for spelling, register in (("1", "%eax"), ("(long)1", "%rax")):
            assembly = compile_program(f"int main(void){{switch({spelling}){{case 1:return 42;}}return 0;}}").stdout
            self.assertIn(f"  cmp $1, {register}\n", assembly)
        for source, message in [("int main(void){case 1:return 0;}", "stray case"),
                                ("int main(void){default:return 0;}", "stray default")]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_continue_statements(self):
        for source, expected in [
            ("int main(void){int s=0;for(int i=0;i<10;i++){if(i>5)continue;s++;}return s;}", 6),
            ("int main(void){int i=0,s=0;while(i++<10){if(i>5)continue;s++;}return s;}", 5),
            ("int main(void){int s=0;for(int i=0;i<3;i++){for(int j=0;j<2;j++)continue;s++;}return s;}", 3),
            ("int main(void){int s=0;for(int i=0;i<3;i++){for(int j=0;j<2;j++)break;continue;s++;}return s;}", 0),
        ]:
            self.assert_program_returns(source, expected)
        loop = parse_body("for(int i=0;i<2;i++)continue;").body.body[0]
        self.assertEqual(loop.then.unique_label, loop.cont_label)
        assembly = compile_program("int main(void){for(int i=0;i<2;i++)continue;}").stdout
        label_position = assembly.index(f"{loop.cont_label}:\n")
        back_edge = assembly.index("  jmp .L.begin.", label_position)
        self.assertIn("  add %edi, %eax\n", assembly[label_position:back_edge])
        result = compile_program("int main(void){continue;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stray continue", result.stderr)

    def test_break_statements(self):
        for source, expected in [
            ("int main(void){int i=0;for(;;i++){if(i==42)break;}return i;}", 42),
            ("int main(void){int i=0;while(1){if(i++==3)break;}return i;}", 4),
            ("int main(void){int i=0;for(;i<10;i++){while(1)break;if(i==3)break;}return i;}", 3),
            ("int main(void){int i=0;for(;;i++){break;}return i;}", 0),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("while(1)break;")
        loop = function.body.body[0]
        self.assertEqual(loop.then.unique_label, loop.brk_label)
        assembly = compile_program("int main(void){while(1)break;}").stdout
        self.assertIn(f"  jmp {loop.brk_label}\n", assembly)
        self.assertIn(f"  je {loop.brk_label}\n", assembly)
        result = compile_program("int main(void){break;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("stray break", result.stderr)

    def test_typedef_label_names(self):
        self.assert_program_returns("typedef int T;int main(void){goto T;return 1;T:;T x=42;return x;}", 42)
        self.assert_program_returns("int main(void){typedef int T;goto T;T:return sizeof(T);}", 4)
        function = parse_body("typedef int T;goto T;T:return 42;")
        jump, label = function.body.body
        self.assertEqual((jump.kind, label.kind), ("GOTO", "LABEL"))
        self.assertEqual(jump.unique_label, label.unique_label)
        self.assertIn("  jmp .L..", compile_program("typedef int T;int main(void){goto T;T:return 42;}").stdout)

    def test_goto_labels(self):
        for source, expected in [
            ("int main(void){goto done;return 1;done:return 42;}", 42),
            ("int main(void){int x=0;again:++x;if(x<3)goto again;return x;}", 3),
            ("int main(void){goto done;{done:return 42;}}", 42),
            ("int f(void){goto a;a:return 3;}int main(void){goto a;a:return f()+39;}", 42),
            ("int main(void){int x=42;goto x;x:return x;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("goto done;done:return 42;")
        jump, label = function.body.body
        self.assertEqual(jump.unique_label, label.unique_label)
        assembly = compile_program("int main(void){goto done;done:return 42;}").stdout
        self.assertIn(f"  jmp {label.unique_label}\n", assembly)
        self.assertIn(f"{label.unique_label}:\n", assembly)
        for source in ("int main(void){goto missing;}", "int f(void){a:return 0;}int main(void){goto a;}"):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("use of undeclared label", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_incomplete_structs(self):
        for source, expected in [
            ("int main(void){struct T *p;return sizeof(p);}", 8),
            ("int main(void){typedef struct T T;struct T{int x;};return sizeof(T);}", 4),
            ("struct T{struct T *next;int x;};int main(void){struct T a,b;b.x=42;a.next=&b;return a.next->x;}", 42),
            ("int main(void){union T *p;union T{long x;char y;};return sizeof(*p);}", 8),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("struct T *p;struct T{int x;};struct T a;")
        a, p = function.locals
        self.assertIs(p.ty.base, a.ty)
        self.assertEqual((a.ty.size, a.ty.align), (4, 4))
        result = compile_program("int main(void){struct T x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("variable has incomplete type", result.stderr)
        self.assertIn("  add $8, %rax\n", compile_program("struct T{struct T *next;int x;};int main(void){struct T a;return a.x;}").stdout)

    def test_array_parameter_decay(self):
        for source, expected in [
            ("int f(int x[]){return x[1];}int main(void){int a[2];a[1]=42;return f(a);}", 42),
            ("int f(int x[3]){return sizeof(x);}int main(void){int a[3];return f(a);}", 8),
            ("int f(int x[][3]){return x[1][2];}int main(void){int a[2][3];a[1][2]=42;return f(a);}", 42),
            ("int f(int *x[]){return *x[0];}int main(void){int x=42;int *a[1];a[0]=&x;return f(a);}", 42),
        ]:
            self.assert_program_returns(source, expected)
        function = parse(tokenize("int f(int x[][3]){return 0;}"))[0]
        param = function.params[0]
        self.assertEqual((param.ty.kind, param.ty.size, param.ty.base.kind, param.ty.base.array_len),
                         ("PTR", 8, "ARRAY", 3))
        self.assertEqual(param.ty.name.text, "x")
        assembly = compile_program("int f(int x[]){return x[0];}").stdout
        self.assertIn("  mov %rdi, -8(%rbp)\n", assembly)

    def test_incomplete_arrays(self):
        self.assert_program_returns("int main(void){return sizeof(int(*)[][10]);}", 8)
        self.assert_program_returns("int main(void){int a[2];a[1]=42;int (*p)[]=a;return (*p)[1];}", 42)
        ty = parse_body("int (*p)[][10];").locals[0].ty
        self.assertEqual((ty.kind, ty.size, ty.base.array_len, ty.base.size), ("PTR", 8, -1, -40))
        for source in ("int main(void){int x[];}", "int main(void){int x[][10];}"):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("variable has incomplete type", result.stderr)
            self.assertEqual(result.stdout, "")
        self.assertIn("  mov $8, %rax\n", compile_program("int main(void){return sizeof(int(*)[]);}").stdout)

    def test_logical_short_circuit(self):
        for source, expected in [
            ("int main(void){int x=42;0&&++x;return x;}", 42),
            ("int main(void){int x=42;1||++x;return x;}", 42),
            ("int main(void){int x=0;1&&++x;0||++x;return x;}", 2),
            ("int main(void){int *p=0;return p&&*p;}", 0),
            ("int main(void){return 1||0&&0;}", 1),
            ("int main(void){return 3&&5;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){return (1&&2)||(0&&3);}").stdout
        labels = [line for line in assembly.splitlines() if line.startswith(".L.") and line.endswith(":")]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertIn("  je .L.false.", assembly)
        self.assertIn("  jne .L.true.", assembly)

    def test_binary_bitwise(self):
        for source, expected in [
            ("int main(void){return 1|2^3&4;}", 3),
            ("int main(void){return 4&1==0;}", 0),
            ("int main(void){int x=6;x&=3;x|=8;return x^=5;}", 15),
            ("int main(void){int x=42;return *&x & 255;}", 42),
            ("int main(void){return (4294967296|42)/4294967296;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        node = grammar_tree(parse_body("return 1|2^3&4;").body.body[0].lhs)
        self.assertEqual((node.kind, node.rhs.kind, node.rhs.rhs.kind), ("|", "^", "&"))
        for spelling, instruction in (("&", "and"), ("|", "or"), ("^", "xor")):
            self.assertIn(f"  {instruction} %edi, %eax\n",
                          compile_program(f"int main(void){{return 7{spelling}3;}}").stdout)

    def test_remainder(self):
        for source, expected in [
            ("int main(void){return 17%6;}", 5),
            ("int main(void){return -17%6==-5;}", 1),
            ("int main(void){return 17%-6;}", 5),
            ("int main(void){return (long)-17%6==-5;}", 1),
            ("int main(void){int x=10;return x%=4;}", 2),
            ("int main(void){int a[2];a[0]=10;int i=0;a[i++]%=4;return i+a[0];}", 3),
        ]:
            self.assert_program_returns(source, expected)
        for spelling, extend, divisor in (("int", "cdq", "%edi"), ("long", "cqo", "%rdi")):
            assembly = compile_program(f"int main(void){{{spelling} x=17;return x%6;}}").stdout
            self.assertIn(f"  {extend}\n  idiv {divisor}\n  mov %rdx, %rax\n", assembly)

    def test_bitwise_not(self):
        for expression, expected in [("~0", 255), ("~-1", 0), ("~~42", 42),
                                     ("~(long)0==-1", 1), ("sizeof(~(char)0)", 1)]:
            self.assert_program_returns(f"int main(void){{return {expression};}}", expected)
        node = parse_body("return ~(short)1;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.ty.kind), ("BITNOT", "SHORT"))
        self.assertIn("  not %rax\n", compile_program("int main(void){return ~0;}").stdout)

    def test_logical_not(self):
        for expression, expected in [("!0", 1), ("!42", 0), ("!!42", 1),
                                     ("!(long)4294967296", 0), ("sizeof(!(char)0)", 4)]:
            self.assert_program_returns(f"int main(void){{return {expression};}}", expected)
        self.assert_program_returns("int main(void){int x;return !&x;}", 0)
        node = parse_body("return !0;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.ty.kind), ("NOT", "INT"))
        self.assertIn("  cmp $0, %rax\n  sete %al\n  movzx %al, %rax\n",
                      compile_program("int main(void){return !0;}").stdout)

    def test_integer_bases(self):
        for spelling, value in [("0777", 511), ("0xbeef", 48879), ("0XBEEF", 48879),
                                ("0b101111", 47), ("0B101111", 47), ("0", 0), ("42", 42)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.text, token.value), (spelling, value))
            self.assert_program_returns(f"int main(void){{return {spelling};}}", value & 255)
        for spelling in ("08", "0b2", "0xG", "123abc", "0x"):
            self.assertEqual(compile_program(f"int main(void){{return {spelling};}}").returncode, 1)
        self.assertIn("  mov $42, %rax\n", compile_program("int main(void){return 0x2a;}").stdout)

    def test_postfix_increment(self):
        for source, expected in [
            ("int main(void){int x=2;return x++;}", 2),
            ("int main(void){int x=2;x--;return x;}", 1),
            ("int main(void){int a[2];a[0]=3;a[1]=42;int *p=a;int x=*p++;return x+*p;}", 45),
            ("int main(void){int a[2];a[0]=3;a[1]=7;int i=0;a[i++]++;return i+a[0]+a[1];}", 12),
            ("int main(void){char x=127;int y=x++;return y==127;}", 1),
            ("int main(void){char x=1;int s=sizeof(x++);return x+s;}", 2),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("char x=1;x++;")
        node = function.body.body[-1].lhs
        self.assertEqual((node.kind, node.ty.kind), ("CAST", "CHAR"))
        self.assertEqual(len([var for var in function.locals if var.name == ""]), 1)
        self.assertEqual(compile_program("int main(void){return 1++;}").returncode, 1)

    def test_prefix_increment(self):
        for source, expected in [
            ("int main(void){int x=2;return ++x;}", 3),
            ("int main(void){int x=2;return --x;}", 1),
            ("int main(void){int a[2];a[1]=42;int *p=a;return *++p;}", 42),
            ("int main(void){int a[2];a[1]=3;int i=0;++a[i+=1];return i+a[1];}", 5),
            ("int main(void){char x=1;int s=sizeof(++x);return x+s;}", 2),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){int x=2;return ++x;}").stdout
        self.assertIn("  add %edi, %eax\n", assembly)
        self.assertEqual([token.text for token in tokenize("++ --")[:-1]], ["++", "--"])
        self.assertEqual(compile_program("int main(void){return ++1;}").returncode, 1)

    def test_compound_assignments(self):
        for source, expected in [
            ("int main(void){int x=2;return x+=5;}", 7),
            ("int main(void){int x=12;x-=2;x*=3;return x/=5;}", 6),
            ("int main(void){int a[2];a[0]=3;a[1]=7;int i=0;a[i=i+1]+=5;return i+a[1];}", 13),
            ("int main(void){int a[2];a[1]=42;int *p=a;p+=1;return *p;}", 42),
            ("int main(void){char x=127;x+=1;return x<0;}", 1),
            ("int main(void){int x=1,y=2;x+=y*=3;return x+y;}", 13),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body("int x=2;x+=5;")
        node = grammar_tree(function.body.body[-1].lhs)
        self.assertEqual((node.kind, node.lhs.kind, node.rhs.kind), ("COMMA", "ASSIGN", "ASSIGN"))
        self.assertEqual(function.locals[0].name, "")
        self.assertEqual(function.locals[0].ty.kind, "PTR")
        self.assertEqual([token.text for token in tokenize("+= -= *= /=")[:-1]], ["+=", "-=", "*=", "/="])
        self.assertEqual(compile_program("int main(void){1+=2;}").returncode, 1)

    def test_for_declarations(self):
        for source, expected in [
            ("int main(void){int s=0;for(int i=0;i<=10;i=i+1)s=s+i;return s;}", 55),
            ("int main(void){int i=42;for(int i=0;i<3;i=i+1);return i;}", 42),
            ("int main(void){int s=0;for(int i=0;i<2;i=i+1)for(int i=0;i<3;i=i+1)s=s+1;return s;}", 6),
        ]:
            self.assert_program_returns(source, expected)
        node = parse_body("for(int i=0;i<1;i=i+1);").body.body[0]
        self.assertEqual(node.init.kind, "BLOCK")
        self.assertEqual(grammar_tree(node.init.body[0].lhs).kind, "ASSIGN")
        result = compile_program("int main(void){for(int i=0;i<1;i=i+1);return i;}")
        self.assertIn("undefined variable", result.stderr)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(compile_program("int main(void){for(static int i=0;;);}").returncode, 1)

    def test_static_functions(self):
        source = "static int f(void){return 42;}int main(void){return f();}"
        self.assert_program_returns(source, 42, "static int f(void){return 5;}")
        assembly = compile_program(source).stdout
        self.assertIn("  .local f\n", assembly)
        self.assertNotIn("  .globl f\n", assembly)
        self.assertIn("  .globl main\n", assembly)
        prototype = parse(tokenize("int static f();"))[0]
        self.assertTrue(prototype.is_static)
        self.assertFalse(prototype.is_definition)
        for source, message in [
            ("typedef static extern int T;", "typedef may not be used together with static or extern"),
            ("int f(static int x);", "storage class specifier is not allowed"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_enum_types(self):
        for source, expected in [
            ("enum E{zero,five=5,six};int main(void){enum E x=six;return x;}", 6),
            ("int main(void){enum {a=3,b,c=1,d};return b+d;}", 6),
            ("enum E{a=5};int main(void){{enum E{a=9};}return a;}", 5),
            ("enum {a=5};int main(void){int a=42;return a;}", 42),
            ("int main(void){enum {a} x;return sizeof(x);}", 4),
        ]:
            self.assert_program_returns(source, expected)
        function = parse(tokenize("enum {answer=42};int main(void){return answer;}"))[0]
        self.assertEqual(function.locals, [])
        self.assertIn("  mov $42, %rax\n", compile_program("enum {answer=42};int main(void){return answer;}").stdout)
        for source, message in [
            ("enum Missing x;", "unknown enum type"),
            ("struct E{int a;};enum E x;", "not an enum tag"),
            ("int main(void){{enum {a};}return a;}", "undefined variable"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_character_literals(self):
        for spelling, value in [("'a'", 97), (r"'\n'", 10), (r"'\x80'", -128),
                                (r"'\377'", -1), (r"'\''", 39), ("'ab'", 97)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.kind, token.text, token.value), ("NUM", spelling, value))
            self.assert_program_returns(f"int main(void){{return {spelling};}}", value & 255)
        self.assert_program_returns(r"int main(void){return '\x80'<0;}", 1)
        self.assert_program_returns("int main(void){return sizeof('a');}", 4)
        self.assertIn("  mov $97, %rax\n", compile_program("int main(void){return 'a';}").stdout)
        for source in ["'", "'a", "'\\"]:
            with self.assertRaises(CompileError) as error:
                tokenize(source)
            self.assertIn("unclosed char literal", str(error.exception))

    def test_bool_type(self):
        for source, expected in [
            ("int main(void){_Bool x=256;return x;}", 1),
            ("int main(void){return (_Bool)0;}", 0),
            ("int main(void){return (_Bool)(char)256;}", 0),
            ("int main(void){return (_Bool)4294967296;}", 1),
            ("int main(void){int x;return (_Bool)&x;}", 1),
            ("_Bool f(_Bool x){return x+1;}int main(void){return f(0);}", 1),
            ("int main(void){_Bool x;return sizeof(x)+sizeof(x+1);}", 5),
        ]:
            self.assert_program_returns(source, expected)
        for value, register in ((256, "%eax"), (4294967296, "%rax")):
            assembly = compile_program(f"int main(void){{return (_Bool){value};}}").stdout
            self.assertIn(f"  cmp $0, {register}\n", assembly)
            self.assertIn("  setne %al\n  movzx %al, %eax\n", assembly)
        self.assertEqual(tokenize("_Bool")[0].kind, "KEYWORD")

    def test_argument_conversions(self):
        for source, expected in [
            ("int f(long a,long b){return a/b;}int main(void){return f(-10,2)==-5;}", 1),
            ("int f(char x){return x;}int main(void){return f(261);}", 5),
            ("int f(short x){return x<0;}int main(void){return f(65535);}", 1),
        ]:
            self.assert_program_returns(source, expected)
        call = parse(tokenize("int f(long x);int main(void){return f(-1);}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.func_ty.kind, "FUNC")
        self.assertEqual((call.args[0].kind, call.args[0].ty.kind), ("CAST", "LONG"))
        assembly = compile_program("int f(long x);int main(void){return f(-1);}").stdout
        self.assertIn("  movsxd %eax, %rax\n", assembly)
        for kind in ("struct", "union"):
            result = compile_program(f"{kind} T{{int x;}};int f({kind} T x);int main(void){{{kind} T a;return f(a);}}")
            self.assertIn("passing struct or union is not supported yet", result.stderr)
            self.assertEqual(result.returncode, 1)

    def test_return_conversions(self):
        for source, expected in [
            ("char f(int x){return x;}int main(void){return f(261);}", 5),
            ("short f(void){return 65535;}int main(void){return f()<0;}", 1),
            ("long f(void){return -1;}int main(void){return f()<0;}", 1),
            ("int x;int *f(void){return &x;}int main(void){x=42;return *f();}", 42),
        ]:
            self.assert_program_returns(source, expected)
        node = parse(tokenize("char f(void){return 261;}"))[0].body.body[0].lhs
        self.assertEqual((node.kind, node.ty.kind, node.lhs.kind), ("CAST", "CHAR", "NUM"))
        assembly = compile_program("char f(void){return 261;}").stdout
        self.assertIn("  movsbl %al, %eax\n  jmp .L.return.f", assembly)

    def test_declared_calls(self):
        self.assert_program_returns("int f();int main(void){return f();}int f(void){return 42;}", 42)
        call = parse(tokenize("char f();int main(void){return f();}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.ty.kind, "CHAR")
        self.assert_program_returns("int f(int x){if(x==0)return 42;return f(x-1);}int main(void){return f(3);}", 42)
        for source, message in [
            ("int main(void){return missing();}", "implicit declaration of a function"),
            ("int main(void){int f;return f();}", "not a function"),
            ("typedef int f;int main(void){return f();}", "not a function"),
            ("int f();int main(void){int f;return f();}", "not a function"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
            self.assertEqual(result.stdout, "")

    def test_usual_arithmetic_conversions(self):
        for source, expected in [
            ("int main(void){int x=-10;long y=5;return (x+y)==-5;}", 1),
            ("int main(void){char x=-1;short y=2;return sizeof(x+y);}", 4),
            ("int main(void){char x=-1;long y=2;return x+y;}", 1),
            ("int main(void){long x=(int)4294967295;return x<0;}", 1),
            ("int main(void){int a[2];a[0]=42;int i=-1;int *p=a+1;return p[i];}", 42),
            ("int main(void){return sizeof(1)+sizeof(1==2);}", 8),
            ("int main(void){return 1073741824*100/100;}", 0),
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
        assembly = compile_program("int main(void){char x=-1;long y=x;return y<0;}").stdout
        self.assertIn("  movsbl (%rax), %eax\n", assembly)
        self.assertIn("  movsxd %eax, %rax\n", assembly)

    def test_explicit_casts(self):
        for source, expected in [
            ("int main(void){return (long)(short)65535<0;}", 1),
            ("int main(void){return (long)(char)255<0;}", 1),
            ("int main(void){int x=-1;return (long)x<0;}", 1),
            ("int main(void){int x=0;(void)(x=7);return x;}", 7),
            ("typedef int T;int main(void){return (T)42;}", 42),
            ("typedef int T;int main(void){long T=3;return (T)+1;}", 4),
            ("int main(void){int a[2];a[0]=42;int i=-1;int *p=a+1;return *(p+(long)i);}", 42),
            ("int main(void){return sizeof((short)1);}", 2),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){return (long)(short)(char)255;}").stdout
        self.assertIn("  movsbl %al, %eax\n", assembly)
        self.assertIn("  movsxd %eax, %rax\n", assembly)
        node = parse_body("return (short)1;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.ty.kind, node.lhs.ty.kind, node.tok.text),
                         ("CAST", "SHORT", "INT", "("))
        for source in ["int main(void){return (int 1;}", "int main(void){return (int);}"]:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_binary_register_widths(self):
        for spelling in ["int", "long"]:
            source = "int main(void){" + spelling + " x=7,y=3;return (x+y)*(x-y)/y;}"
            self.assert_program_returns(source, 13)
            assembly = compile_program(source).stdout
            ax, di = ("%eax", "%edi") if spelling == "int" else ("%rax", "%rdi")
            for instruction in ["add", "sub", "imul"]:
                self.assertIn(f"  {instruction} {di}, {ax}\n", assembly)
            extension = "cdq" if spelling == "int" else "cqo"
            self.assertIn(f"  {extension}\n  idiv {di}\n", assembly)
        for spelling in ["char", "short", "int", "long"]:
            self.assert_program_returns("int main(void){" + spelling + " x=-7;return x/2;}", 253)
            assembly = compile_program("int main(void){" + spelling + " x=3;return x<4;}").stdout
            comparison = "  cmp %rdi, %rax\n" if spelling == "long" else "  cmp %edi, %eax\n"
            self.assertIn(comparison, assembly)
        self.assert_program_returns("int main(void){int x=65536;return x*x;}", 0)
        assembly = compile_program("int main(void){int x;int *p=&x;return (p+1)-p;}").stdout
        self.assertIn("  add %rdi, %rax\n", assembly)
        self.assertIn("  sub %rdi, %rax\n", assembly)
        self.assertIn("  cqo\n  idiv %rdi\n", assembly)

    def test_sizeof_type_names(self):
        for source, expected in [
            ("typedef int T;int main(void){return sizeof(T);}", 4),
            ("typedef char T;int main(void){long T;return sizeof(T);}", 8),
            ("int main(void){return sizeof(void);}", 1),
            ("int main(void){return sizeof(long long int);}", 8),
            ("int main(void){return sizeof(int(**)[3]);}", 8),
            ("int main(void){return sizeof(int(*[2])[3]);}", 16),
            ("int main(void){return sizeof(int (*)(int x));}", 8),
        ]:
            self.assert_program_returns(source, expected)
        actual = compile_program("int main(void){return sizeof(int*[4]);}")
        expected = compile_program("int main(void){return 32;}")
        self.assertEqual(instruction_assembly(actual.stdout), instruction_assembly(expected.stdout))
        for source, message in [
            ("int main(void){return sizeof(int[3]);}", None),
            ("int main(void){return sizeof(int[3];}", "expected ')'"),
            ("int main(void){return sizeof(typedef int T);}", "storage class specifier is not allowed in this context"),
        ]:
            result = compile_program(source)
            if message is None:
                self.assertEqual(result.returncode, 0, result.stderr)
            else:
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_typedefs(self):
        for source, expected in [
            ("typedef int Row[3];int main(void){Row a[2];Row *p=a;p[1][2]=42;return a[1][2];}", 42),
            ("typedef long L;L twice(L x){return x+x;}int main(void){return twice(2147483648)/65536/65536;}", 1),
            ("typedef int T;int main(void){{int T=3;}T x=42;return x;}", 42),
            ("typedef int T;int main(void){int T=3;{typedef char T;T c=2;}return T;}", 3),
            ("int main(void){typedef int t;t t=3;return t;}", 3),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual(compile_program("typedef int T;").stdout, '.file 1 "-"\n')
        program = parse_body("typedef int T;T x=1;")
        self.assertEqual([var.name for var in program.locals], ["x"])
        for source, message in [
            ("int main(void){{typedef int T;}T x;}", "undefined variable"),
            ("int main(void){typedef int T;return T;}", "undefined variable"),
            ("int f(typedef int x);", "storage class specifier is not allowed in this context"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_long_long_alias(self):
        for spelling in ["long long", "long long int", "int long long", "long int long"]:
            self.assert_program_returns("int main(void){" + spelling + " x;return sizeof(x);}", 8)
            ty = parse_body(spelling + " x;").locals[0].ty
            self.assertEqual((ty.kind, ty.size, ty.align), ("LONG", 8, 8))
        self.assert_program_returns("int main(void){long long x=4294967296;return x/65536/65536;}", 1)
        for spelling in ["long long long", "long long int int", "short long long"]:
            result = compile_program("int main(void){" + spelling + " x;}")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid type", result.stderr)

    def test_type_specifier_combinations(self):
        for spelling, size in [("char", 1), ("short int", 2), ("int short", 2),
                               ("int", 4), ("long int", 8), ("int long", 8)]:
            self.assert_program_returns("int main(void){" + spelling + " x;return sizeof(x);}", size)
        self.assert_program_returns("main(void){return 42;}", 42)
        self.assert_program_returns("int f(x){return x;}main(void){return f(42);}", 42)
        for spelling in ["char int", "int int", "void int", "short long"]:
            result = compile_program("int main(void){" + spelling + " x;}")
            self.assertEqual(result.returncode, 1)
            self.assertIn("invalid type", result.stderr)

    def test_void_type(self):
        for source, expected in [
            ("int main(void){void *p;return sizeof(p);}", 8),
            ("int main(void){int x=42;void *p=&x;int *q=p;return *q;}", 42),
            ("void f();void f(void){}int main(void){f();return 42;}", 42),
            ("int main(void){int x;void *p=&x;return (p+1)-p;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual((ty_void.size, ty_void.align), (1, 1))
        self.assertEqual(parse_body("void *p;").locals[0].ty.base.kind, "VOID")
        for source, message in [("int main(void){void x;}", "variable declared void"),
                                ("int main(void){void *p;return *p;}", "dereferencing a void pointer"),
                                ("int main(void){void *p;sizeof(*p);}", "dereferencing a void pointer")]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn(message, result.stderr)

    def test_function_declarations(self):
        self.assert_program_returns("int f(int x);int main(void){return f(42);}int f(int x){return x;}", 42)
        self.assert_program_returns("int ret42();int main(void){return ret42();}", 42,
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
        self.assertEqual(compile_program("int f(int); ").returncode, 0)

    def test_nested_declarators(self):
        for source, expected in [
            ("int (main)(){return 42;}", 42),
            ("int main(void){char *(*x[2])[3];return sizeof(x);}", 16),
            ("int main(void){int a[2][3];int (*p)[3]=a;p[1][2]=42;return a[1][2];}", 42),
            ("int f(int (*p)[3]){return p[0][2];}int main(void){int a[3];a[2]=42;return f(a);}", 42),
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
        result = compile_program("int main(void){int (*x;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected ')'", result.stderr)

    def test_short_type(self):
        for source, expected in [
            ("int main(void){short x;return sizeof(x);}", 2),
            ("int main(void){short x=32768;return x<0;}", 1),
            ("short g;int main(void){g=65535;return g==-1;}", 1),
            ("int main(void){short x=7;short y=9;x=11;return y;}", 9),
            ("int main(void){short a[3];a[2]=42;return *(a+2);}", 42),
            ("int main(void){struct {char a;short b;} x;return sizeof(x);}", 4),
            ("int f(short a,short b,short c,short d,short e,short f){return a+b+c+d+e+f;}int main(void){return f(1,2,3,4,5,6);}", 21),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("short f(short a){return a;}int main(void){short x=42;return f(x);}").stdout
        self.assertIn("  mov %di, -2(%rbp)\n", assembly)
        self.assertIn("  mov %ax, (%rdi)\n", assembly)
        self.assertIn("  movswl (%rax), %eax\n", assembly)
        self.assertEqual((ty_short.size, ty_short.align), (2, 2))

    def test_long_type(self):
        for source, expected in [
            ("int main(void){long x=4294967296;return x/65536/65536;}", 1),
            ("long g;int main(void){g=9223372036854775807;return g==9223372036854775807;}", 1),
            ("long f(long x){return x+1;}int main(void){return f(4294967296)/65536/65536;}", 1),
            ("int main(void){long a[2];a[0]=3;a[1]=4;return *(a+1);}", 4),
            ("int main(void){struct {char a;long b;} x;return sizeof(x);}", 16),
            ("long missing();int main(void){return sizeof(1)+sizeof(1==2)+sizeof(missing());}", 16),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("long f(long a){return a;}int main(void){long x=4294967296;return f(x)/65536/65536;}").stdout
        self.assertIn("  mov $4294967296, %rax\n", assembly)
        self.assertIn("  mov %rdi, -8(%rbp)\n", assembly)
        self.assertIn("  mov %rax, (%rdi)\n", assembly)
        self.assertEqual((ty_long.size, ty_long.align), (8, 8))
        self.assertIs(parse_body("return 1;").body.body[0].lhs.lhs.ty, ty_int)
        self.assertEqual(tokenize("9223372036854775807")[0].value, 9223372036854775807)
        self.assertEqual(tokenize("short")[0].kind, "KEYWORD")
        result = compile_program("int main(void){short x;}")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = compile_program("int main(void){return 18446744073709551616;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsigned 64 bits", result.stderr)

    def test_four_byte_ints(self):
        for source, expected in [
            ("int main(void){int x;int *p=&x;return sizeof(x)+sizeof(p);}", 12),
            ("int main(void){int x=2147483647+1;return x<0;}", 1),
            ("int main(void){int x=65536*65536;return x;}", 0),
            ("int main(void){int x=7;int y=9;x=11;return y;}", 9),
            ("int f(int x){return x<0;}int main(void){return f(-1);}", 1),
            ("int f(char c,int x,int *p,int y,char d,int z){return c+x+*p+y+d+z;}int main(void){int v=7;return f(1,2,&v,3,4,5);}", 22),
        ]:
            self.assert_program_returns(source, expected)
        self.assert_program_returns("int sum(int *a);int main(void){int a[2];a[0]=3;a[1]=4;return sum(a);}", 7,
                                    "int sum(int *a){return a[0]+a[1];}")
        assembly = compile_program("int main(void){int x=42;return x;}").stdout
        self.assertIn("  mov %eax, (%rdi)\n", assembly)
        self.assertIn("  movsxd (%rax), %rax\n", assembly)
        self.assertEqual((ty_int.size, ty_int.align), (4, 4))

    def test_aggregate_assignment(self):
        for source, expected in [
            ("int main(void){struct t{int a,b;} x,y,z;x.a=3;x.b=7;z=y=x;return z.a+y.b;}", 10),
            ("int main(void){struct t{char a[17];} x,y;x.a[16]=42;y=x;return y.a[16];}", 42),
            ("int main(void){struct t{char a;int b;} x,y;char *p=&x;int i;for(i=0;i<sizeof(x);i=i+1)p[i]=i;y=x;char *q=&y;return q[7];}", 7),
            ("int main(void){union t{int a;char b[4];} x,y;x.a=515;y=x;return y.b[1];}", 2),
            ("struct t{int a;} g;int main(void){struct t x;x.a=42;g=x;return g.a;}", 42),
            ("int main(void){struct t{int a;} x;x.a=42;x=x;struct t y;y=x;return y.a;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){struct {char a[3];} x,y;y=x;return 0;}").stdout
        for offset in range(3):
            self.assertIn(f"  mov {offset}(%rax), %r8b\n  mov %r8b, {offset}(%rdi)\n", assembly)
        self.assertNotIn("  mov 3(%rax), %r8b", assembly)

    def test_unions(self):
        for source, expected in [
            ("int main(void){union t{int a;char b[4];} x;union t *p=&x;p->a=515;return p->b[0]+p->b[1];}", 5),
            ("union t{int a;char b[4];};union t g;int main(void){g.a=515;return g.b[1];}", 2),
            ("int main(void){union t{int a;};{union t{char a;};}union t x;return sizeof(x);}", 4),
            ("int main(void){union {int a;char b[9];} x[2];char *p=x;char *q=x+1;return q-p;}", 12),
        ]:
            self.assert_program_returns(source, expected)
        ty = parse_body("union {int a;char b[9];} x;").locals[0].ty
        self.assertEqual((ty.kind, ty.size, ty.align), ("UNION", 12, 4))
        self.assertEqual([member.offset for member in ty.members], [0, 0])
        ty = parse_body("struct {char a;union {int b;char c[9];} d;} x;").locals[0].ty
        self.assertEqual((ty.size, ty.members[1].offset), (16, 4))

    def test_member_arrow(self):
        for source, expected in [
            ("int main(void){struct t{char a;} x;struct t *y=&x;x.a=3;return y->a;}", 3),
            ("int main(void){struct t{char a;} x;struct t *y=&x;y->a=3;return x.a;}", 3),
            ("int main(void){struct t{int a;} x[2];struct t *p=x;p[1].a=7;return (p+1)->a;}", 7),
            ("int main(void){struct n{int v;} x;struct h{struct n *p;} y;struct h *z=&y;y.p=&x;z->p->v=42;return x.v;}", 42),
        ]:
            self.assert_program_returns(source, expected)
        prefix = "int main(void){struct t{int a;} x;struct t *p=&x;"
        arrow = compile_program(prefix + "return p->a;}")
        dot = compile_program(prefix + "return (*p).a;}")
        self.assertEqual(instruction_assembly(arrow.stdout), instruction_assembly(dot.stdout))
        self.assertEqual(tokenize("p->a")[1].text, "->")
        for source, message in [("int main(void){int x;return x->a;}", "invalid pointer dereference"),
                                ("int main(void){int x;int *p=&x;return p->a;}", "not a struct")]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_struct_tags(self):
        for source, expected in [
            ("struct t{int a;};struct t g;int main(void){g.a=5;return g.a;}", 5),
            ("int main(void){struct t{int a;};{struct t{char a;};struct t x;return sizeof(x);}}", 1),
            ("int main(void){struct t{int a;};{struct t{char a;};}struct t x;return sizeof(x);}", 4),
            ("int main(void){struct t{int a;};int t=3;struct t x;x.a=4;return t+x.a;}", 7),
        ]:
            self.assert_program_returns(source, expected)
        for source in ["int main(void){struct missing x;}",
                       "int main(void){{struct t{int a;};}struct t x;}"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("variable has incomplete type", result.stderr)

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
        self.assert_program_returns("int main(void){int x;int y;char z;char *a=&y;char *b=&z;return b-a;}", 7)
        self.assert_program_returns("int main(void){int x;char y;int z;char *a=&y;char *b=&z;return b-a;}", 1)

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
        self.assert_program_returns("int main(void){struct {char a;int b;} x;char *p=&x;char *q=&x.b;return q-p;}", 4)
        self.assert_program_returns("int main(void){struct {char a;int b;} x[2];char *p=x;char *q=x+1;return q-p;}", 8)
        ty = parse_body("struct {char a;int b;} x[2];").locals[0].ty
        self.assertEqual((ty.size, ty.align), (16, 4))

    def test_struct_members(self):
        for source, expected in [
            ("int main(void){struct {char a;int b;char c;} x;x.a=1;x.b=2;x.c=3;return x.a+x.b+x.c;}", 6),
            ("struct {int a;char b;} g;int main(void){g.a=7;g.b=3;return g.a+g.b;}", 10),
            ("int main(void){struct {char a[3];char b;} x;x.a[2]=5;x.b=7;return x.a[2]+x.b;}", 12),
            ("int main(void){struct {int a;} x;int *p=&x.a;*p=9;return x.a;}", 9),
        ]:
            self.assert_program_returns(source, expected)
        program = parse_body("struct {char a;int b;} x;return sizeof(x);")
        ty = program.locals[0].ty
        self.assertEqual(ty.size, 8)
        self.assertEqual([member.offset for member in ty.members], [0, 4])
        assembly = compile_program("int main(void){struct {char a;int b;} x;x.b=42;return x.b;}")
        self.assertIn("  add $4, %rax\n", assembly.stdout)
        for source, message in [
            ("int main(void){int x;return x.a;}", "not a struct"),
            ("int main(void){struct {int x;} a;return a.y;}", "no such member"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_comma_operator(self):
        for source, expected in [
            ("int main(void){return (1,2,3);}", 3),
            ("int main(void){int i=2,j=3;(i=5,j)=6;return i;}", 5),
            ("int main(void){int i=2,j=3;(i=5,j)=6;return j;}", 6),
            ("int main(void){int x=0;return (x=1,x=x+2,x);}", 3),
            ("int main(void){int i=0,j=2;*(i=5,&j)=6;return i+j;}", 11),
            ("int main(void){char x;return sizeof(1,x);}", 1),
            ("int main(void){int x=(1,2);return x;}", 2),
            ("int pair(int a,int b){return a+b;}int main(void){int x=0;return pair((x=1,7),x);}", 8),
        ]:
            self.assert_program_returns(source, expected)
        node = parse_body("return 1,2,3;").body.body[0].lhs.lhs
        self.assertEqual((node.kind, node.rhs.kind), ("COMMA", "COMMA"))
        self.assertIs(node.ty, ty_int)
        result = compile_program("int main(void){(1,2)=3;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("not an lvalue", result.stderr)

    def test_assembly_source_locations(self):
        source_text = "int main(void){\n return 42;\n}\n"
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
            parse(tokenize("int main(void){\n return missing;\n}"))
        self.assertEqual(caught.exception.line_no, 2)
        error = CompileError(3, "lexical error")
        self.assertIsNone(error.line_no)
        result = compile_program("int main(void){\n Ω\n}")
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
            ("int main(void){int x=2;{int x=3;}return x;}", 2),
            ("int main(void){int x=2;{int x=3;}{int y=4;return x;}}", 2),
            ("int main(void){int x=2;{x=3;}return x;}", 3),
            ("int x;int main(void){x=7;{int x=3;}return x;}", 7),
            ("int main(void){int x=2;return ({int x=3;x;})+x;}", 5),
            ("int f(int x){{int x=3;}return x;}int main(void){return f(7);}", 7),
        ]:
            self.assert_program_returns(source, expected)
        for source in ["int main(void){{int x=2;}return x;}",
                       "int f(void){int x=2;return x;}int main(void){return x;}",
                       "int main(void){({int x=2;x;});return x;}"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("undefined variable", result.stderr)
        program = parse(tokenize("int main(void){int x;{int x;int y;}}"))
        self.assertEqual([var.name for var in program[0].locals], ["y", "x", "x"])

    def test_comments(self):
        for source in ["int main(void){/* return 1; */ return 2;}",
                       "int main(void){// return 1;\nreturn 2;}"]:
            self.assert_program_returns(source, 2)
        plain = compile_program("int main(void){return 42;}")
        commented = compile_program("/*before*/int/*type*/ main(void){return/*value*/42;} //after")
        self.assertEqual(commented.returncode, 0, commented.stderr)
        self.assertEqual(commented.stdout, plain.stdout)
        self.assertEqual(tokenize('"// /* */"')[0].str, b"// /* */\0")
        self.assertEqual(tokenize("// eof")[0].kind, "EOF")
        result = compile_program("int main(void){\n/* unclosed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("-:2: /* unclosed\n", result.stderr)
        self.assertIn("^ unclosed block comment", result.stderr)

    def test_driver_options(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input file.c"
            output = Path(directory) / "output file.s"
            source.write_text("int main(void){return 42;}")
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
            source.write_text("int main(void){1=2;}")
            output.write_text("keep")
            result = subprocess.run([sys.executable, str(COMPILER), "-o", str(output), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_text(), "keep")
            result = subprocess.run([sys.executable, str(COMPILER), "-o", directory, "-"],
                                    input="int main(void){return 0;}", capture_output=True, text=True)
            self.assertIn("cannot open output file", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("chibicc", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "-o"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("chibicc", result.stderr)

    def test_file_input(self):
        source = "int main(void){return 42;}"
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
            path.write_text("int main(void){\n return missing;\n}\n")
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
            self.assert_program_returns("int main(void){"+body+"}", expected)
        for source in ["int main(void){return ({});}", "int main(void){return ({int x;});}",
                       "int main(void){return ({return 1;});}"]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("statement expression returning void", result.stderr)

    def test_hex_string_escapes(self):
        for spelling, expected in [(r"\x00",0),(r"\x77",119),(r"\xA5",165),
                                   (r"\x00ff",255),(r"\x41Z",65),(r"\x1234",52)]:
            self.assert_program_returns('int main(void){return "'+spelling+'"[0];}', expected)
        self.assertEqual(tokenize(r'"\x41Z"')[0].str, b"AZ\0")
        self.assertEqual(tokenize(r'"\x00ff"')[0].ty.size, 2)
        for source in [r'int main(void){return "\x"[0];}', r'int main(void){return "\xg"[0];}']:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("invalid hex escape sequence", result.stderr)

    def test_octal_string_escapes(self):
        for spelling, expected in [(r"\0",0),(r"\20",16),(r"\101",65),
                                   (r"\1500",104),(r"\777",255),(r"\8",56)]:
            self.assert_program_returns('int main(void){return "'+spelling+'"[0];}', expected)
        self.assertEqual(tokenize(r'"\1500"')[0].str, b"h0\0")
        self.assertEqual(tokenize(r'"a\0b"')[0].str, b"a\0b\0")
        self.assert_program_returns(r'int main(void){return sizeof("a\0b");}', 4)
        self.assert_program_returns(r'int main(void){return "\1500"[1];}', 48)

    def test_named_string_escapes(self):
        for escape, expected in [("a",7),("b",8),("t",9),("n",10),("v",11),
                                 ("f",12),("r",13),("e",27),("j",106),("k",107),("l",108)]:
            self.assert_program_returns('int main(void){return "\\'+escape+'"[0];}', expected)
        for index, expected in enumerate([7,120,10,121]):
            self.assert_program_returns(r'int main(void){return "\ax\ny"['+str(index)+'];}', expected)
        self.assert_program_returns(r'int main(void){return "\""[0];}', 34)
        self.assert_program_returns(r'int main(void){return "\\"[0];}', 92)
        self.assertEqual(tokenize(r'"\n"')[0].str, b"\n\0")
        self.assertEqual(tokenize(r'"\n"')[0].ty.size, 2)
        self.assertEqual(compile_program('int main(void){return "abc\\').returncode, 1)

    def test_string_literals(self):
        for body, expected in [('return ""[0];',0), ('return sizeof("");',1),
                               ('return "abc"[0];',97), ('return "abc"[1];',98),
                               ('return "abc"[2];',99), ('return "abc"[3];',0),
                               ('return sizeof("abc");',4), ('return sizeof("é");',3)]:
            self.assert_program_returns("int main(void){"+body+"}", expected)
        token = tokenize('"abc"')[0]
        self.assertEqual(token.str, b"abc\0")
        self.assertEqual(token.ty.size, 4)
        assembly = compile_program('int main(void){return "abc"[0];}').stdout
        self.assertIn("  .byte 97\n  .byte 98\n  .byte 99\n  .byte 0\n", assembly)
        self.assertIn("  lea .L..0(%rip), %rax", assembly)
        for source in ['int main(void){return "abc;}', 'int main(void){return "a\nb"[0];}']:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("unclosed string literal", result.stderr)

    def test_char(self):
        for source, expected in [
            ("int main(void){char x=1;return x;}",1),
            ("int main(void){char x=1;char y=2;return x;}",1),
            ("int main(void){char x=1;char y=2;return y;}",2),
            ("int main(void){char x;return sizeof(x);}",1),
            ("int main(void){char x[10];return sizeof(x);}",10),
            ("int sub_char(char a,char b,char c);int main(void){return sub_char(7,3,3);} int sub_char(char a,char b,char c){return a-b-c;}",1),
            ("int main(void){char x=255;return x<0;}",1),
            ("int main(void){char x=1;int y=513;x=257;return y==513;}",1),
            ("int main(void){char a[3];a[1]=7;return a[1];}",7),
            ("char x;int main(void){x=255;return x<0;}",1),
            ("int f(char a,char b,char c,char d,char e,char f){return a+2*b+3*c+4*d+5*e+6*f;} int main(void){return f(1,2,3,4,5,6);}",91),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program("int main(void){char x=1;return x;}").stdout
        self.assertIn("  mov %al, (%rdi)\n", assembly)
        self.assertIn("  movsbl (%rax), %eax\n", assembly)

    def test_global_variables(self):
        for source, expected in [
            ("int x; int main(void){return x;}",0),
            ("int x; int main(void){x=3; return x;}",3),
            ("int x; int y; int main(void){x=3; y=4; return x+y;}",7),
            ("int x,y; int main(void){x=3; y=4; return x+y;}",7),
            ("int x; int main(void){return sizeof(x);}",4),
            ("int x[4]; int main(void){return sizeof(x);}",16),
            ("int x; int f(void){x=9; return 0;} int main(void){f(); return x;}",9),
            ("int x; int main(void){int x=3; return x;}",3),
        ]:
            self.assert_program_returns(source, expected)
        for index in range(4):
            self.assert_program_returns("int x[4]; int main(void){x[0]=0;x[1]=1;x[2]=2;x[3]=3;"
                                        f"return x[{index}];}}", index)
        assembly = compile_program("int x; int main(void){return x;}").stdout
        self.assertIn("  .globl x\n  .align 4\n  .bss\nx:\n  .zero 4\n", assembly)
        self.assertIn("  lea x(%rip), %rax\n", assembly)
        self.assert_program_returns("int x=3; int main(void){return x;}", 3)
        self.assertEqual(compile_program("int main(void){return x;} int x;").returncode, 1)

    def test_unified_objects(self):
        objects = parse(tokenize("int a(void){int x;return 3;} int main(void){return a();}"))
        self.assertEqual([obj.name for obj in objects], ["main", "a"])
        self.assertTrue(all(obj.is_function and not obj.is_local for obj in objects))
        self.assertTrue(objects[1].locals[0].is_local)
        self.assertEqual(objects[1].ty.kind, "FUNC")
        assembly = CodeGenerator().generate(objects)
        self.assertEqual(assembly.count("  .text\n"), 2)
        self.assert_program_returns("int a(void){return 3;} int main(void){return a();}", 3)

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
            self.assert_program_returns("long missing();int main(void){"+body+"}", expected)
        assembly = compile_program("long missing();int main(void){return sizeof missing();}").stdout
        self.assertNotIn("call", assembly)
        self.assertEqual(compile_program("int main(void){return sizeof *1;}").returncode, 1)
        self.assertEqual(tokenize("sizeof sizeofx")[1].kind, "IDENT")

    def test_subscripts(self):
        for index, expected in [(0,3),(1,4),(2,5)]:
            self.assert_program_returns("int main(void){int x[3]; *x=3; x[1]=4; x[2]=5;"
                                        f"return *(x+{index});}}", expected)
        self.assert_program_returns("int main(void){int x[3]; *x=3; x[1]=4; 2[x]=5; return *(x+2);}", 5)
        for index in range(6):
            self.assert_program_returns("int main(void){int x[2][3]; int *y=x;"
                                        f"y[{index}]={index}; return x[{index//3}][{index%3}];}}", index)
        self.assert_program_returns("int main(void){int x[2]; int i=0; x[i=1]=9; return x[i];}", 9)
        a = compile_program("int main(void){int x[2]; return x[1];}")
        b = compile_program("int main(void){int x[2]; return *(x+1);}")
        self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(compile_program("int main(void){int x[2]; return x[1;}").returncode, 1)

    def test_arrays_of_arrays(self):
        for index, expression in enumerate(["**x", "*(*x+1)", "*(*x+2)",
                                            "**(x+1)", "*(*(x+1)+1)", "*(*(x+1)+2)"]):
            self.assert_program_returns("int main(void){int x[2][3]; int *y=x;"
                                        f"*(y+{index})={index}; return {expression};}}", index)
        function = parse(tokenize("int main(void){int x[2][3]; return x+1;}"))[0]
        ty = function.locals[0].ty
        self.assertEqual((ty.array_len, ty.size, ty.base.array_len, ty.base.size), (2,24,3,12))
        expression = grammar_tree(function.body.body[-1].lhs)
        self.assertEqual(expression.rhs.rhs.value, 12)
        self.assert_program_returns("int main(void){int x[2][3][4]; *(*(*(x+1)+2)+3)=9; return *(*(*(x+1)+2)+3);}", 9)

    def test_one_dimensional_arrays(self):
        self.assert_program_returns("int main(void){int x[2]; int *y=&x; *y=3; return *x;}", 3)
        for offset, expected in [(0,3),(1,4),(2,5)]:
            self.assert_program_returns("int main(void){int x[3]; *x=3; *(x+1)=4; *(x+2)=5;"
                                        f"return *(x+{offset});}}", expected)
        self.assert_program_returns("int main(void){int *x[2]; int a=7; *x=&a; return **x;}", 7)
        function = parse(tokenize("int main(void){int x[3]; return x;}"))[0]
        assembly = CodeGenerator().generate([function])
        self.assertEqual(function.locals[0].ty.size, 12)
        self.assertEqual(function.locals[0].offset, -12)
        self.assertEqual(function.stack_size, 16)
        self.assertIn("  lea -12(%rbp), %rax\n  jmp .L.return.main", assembly)
        for source in ["int main(void){int x[2]; x=3;}", "int main(void){int x[a];}",
                       "int main(void){int x[2;}"]:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_function_parameters(self):
        for source, expected in [
            ("int add2(int x,int y);int main(void){return add2(3,4);} int add2(int x,int y){return x+y;}", 7),
            ("int sub2(int x,int y);int main(void){return sub2(4,3);} int sub2(int x,int y){return x-y;}", 1),
            ("int fib(int x);int main(void){return fib(9);} int fib(int x){if(x<=1)return 1; return fib(x-1)+fib(x-2);}", 55),
            ("int f(int a,int b,int c,int d,int e,int f){return a+2*b+3*c+4*d+5*e+6*f;} int main(void){return f(1,2,3,4,5,6);}", 91),
            ("int set(int *p){*p=9; return *p;} int main(void){int x=1; return set(&x);}", 9),
        ]:
            self.assert_program_returns(source, expected)
        function = parse(tokenize("int f(int x,int y){int z; return x-y;}"))[0]
        self.assertEqual([var.name for var in function.params], ["x", "y"])
        self.assertEqual([var.name for var in function.locals], ["z", "x", "y"])
        assembly = CodeGenerator().generate([function])
        self.assertIn("  mov %edi, -8(%rbp)\n  mov %esi, -12(%rbp)\n", assembly)
        self.assertEqual(compile_program("int f(int a,int b,int c,int d,int e,int f,int g){} ").returncode, 1)
        result = compile_program("int f();int main(void){return f(*3);}")
        self.assertIn("invalid pointer dereference", result.stderr)

    def test_argument_calls(self):
        helpers = """
int add(int x,int y) {return x+y;} int sub(int x,int y) {return x-y;}
int add6(int a,int b,int c,int d,int e,int f) {return a+b+c+d+e+f;}
"""
        declarations = "int add();int sub();int add6();"
        for source, expected in [
            ('int main(void){return add(3,5);}', 8), ('int main(void){return sub(5,3);}', 2),
            ('int main(void){return add6(1,2,3,4,5,6);}', 21),
            ('int main(void){return add6(1,2,add6(3,4,5,6,7,8),9,10,11);}', 66),
            ('int main(void){return add6(1,2,add6(3,add6(4,5,6,7,8,9),10,11,12,13),14,15,16);}', 136),
            ('int main(void){int x=0; return sub(x=5,x=3);}', 2),
        ]:
            self.assert_program_returns(declarations + source, expected, helpers)
        assembly = compile_program(declarations + 'int main(void){return add6(1,2,3,4,5,6);}').stdout
        self.assertIn("  pop %r9\n  pop %r8\n  pop %rcx\n  pop %rdx\n"
                      "  pop %rsi\n  pop %rdi\n", assembly)
        result = compile_program('int f();int main(void){return f(1,2,3,4,5,6,7);}')
        self.assertEqual(result.returncode, 1)
        self.assertIn("at most 6 arguments", result.stderr)
        for source in ['int f();int main(void){return f(1 2);}', 'int f();int main(void){return f(1,);}']:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_zero_argument_calls(self):
        declarations = "int ret3();int ret5();"
        helpers = "int ret3(void) { return 3; } int ret5(void) { return 5; }"
        for source, expected in [('int main(void){return ret3();}', 3), ('int main(void){return ret5();}', 5),
                                 ('int main(void){return ret3()+ret5();}', 8)]:
            self.assert_program_returns(declarations + source, expected, helpers)
        call = parse(tokenize("int ret3();int main(void){return ret3();}"))[0].body.body[0].lhs.lhs
        self.assertEqual(call.funcname, "ret3")
        self.assertEqual(call.ty.kind, "INT")
        assembly = compile_program(declarations + 'int main(void){return ret3();}').stdout
        self.assertIn("  mov $0, %rax\n  call ret3\n", assembly)
        self.assertEqual(compile_program(declarations + 'int main(void){return ret3(,);}').returncode, 1)

    def test_pointer_arithmetic(self):
        for source, expected in [
            ('int main(void){int x=3; int y=5; return *(1+&x);}', 5),
            ('int main(void){int x=3; int y=5; return &y-&x;}', 1),
            ('int main(void){int x=3; int y=5; return &x-&y;}', 255),
            ('int main(void){int x=3; return (&x+3)-(&x+1);}', 2),
            ('int main(void){int x=3; return (&x-2)-&x;}', 254),
            ('int main(void){int x=3; int y=5; int *p=&x; return *(p+1);}', 5),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        expression = grammar_tree(parse_body("int x; return &x+1;").body.body[-1].lhs.lhs)
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.ty.base.kind, "INT")
        self.assertEqual(expression.rhs.kind, "*")
        self.assertEqual(expression.rhs.rhs.value, 4)
        expression = parse_body("int x,y; return &x-&y;").body.body[-1].lhs.lhs
        self.assertEqual(expression.ty.kind, "LONG")
        self.assertEqual(expression.kind, "/")
        self.assertEqual(expression.lhs.ty.kind, "LONG")
        self.assertEqual((expression.lhs.kind, expression.rhs.kind), ("CAST", "CAST"))
        self.assertEqual(expression.rhs.lhs.value, 4)
        expression = parse_body("int x; return &x-1+2;").body.body[-1].lhs.lhs
        self.assertEqual(expression.lhs.ty.kind, "PTR")
        expression = grammar_tree(parse_body("int x; int *p=&x; return p+1;").body.body[-1].lhs.lhs)
        self.assertEqual(expression.ty.kind, "PTR")
        self.assertEqual(expression.rhs.kind, "*")

    def test_address_and_dereference(self):
        for source, expected in [
            ('int main(void){ int x=3; return *&x; }', 3),
            ('int main(void){ int x=3; int *y=&x; int **z=&y; return **z; }', 3),
            ('int main(void){ int x=3; int y=5; return *(&x+1); }', 5),
            ('int main(void){ int x=3; int y=5; return *(&y-1); }', 3),
            ('int main(void){ int x=3; int *y=&x; *y=5; return x; }', 5),
            ('int main(void){ int x=3; int y=5; *(&x+1)=7; return y; }', 7),
            ('int main(void){ int x=3; int y=5; *(&y-1)=7; return x; }', 7),
            ('int main(void){ int x=1; int *p=&x; int **q=&p; **q=9; return x; }', 9),
            ('int main(void){ int x=1; *&x=7; return x; }', 7),
            ('int main(void){ int x=3; int *p=&x; return &*p==p; }', 1),
        ]:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("int *x; 1**x;")
        expression = grammar_tree(program.body.body[1].lhs)
        self.assertEqual(expression.kind, "*")
        self.assertEqual(expression.rhs.kind, "DEREF")
        self.assertEqual(expression.rhs.tok.text, "*")
        result = compile_program('int main(void){int x; return &x;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -4(%rbp), %rax\n  jmp .L.return.main\n" + EPILOGUE)
        result = compile_program('int main(void){int x; return *&x;}')
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  lea -4(%rbp), %rax\n  movsxd (%rax), %rax\n"
                         "  jmp .L.return.main\n" + EPILOGUE)
        for source, position in [('int main(void){return &1;}', 23),
                                 ('int main(void){return &(1+2);}', 25)]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: "))
                             + "^ not an lvalue\n")

    def test_representative_tokens(self):
        source = 'int main(void){return -(1+2)*3>4;}'
        tokens = tokenize(source)
        program = parse(tokens)[0]
        statement = program.body.body[0]
        self.assertIs(program.body.tok, tokens[6])
        self.assertIs(statement.tok, tokens[6])
        comparison = grammar_tree(statement.lhs)
        self.assertEqual(comparison.kind, "<")
        self.assertEqual(comparison.tok.text, ">")
        multiply = comparison.rhs
        self.assertEqual(multiply.tok.position, source.index("*"))
        self.assertEqual(multiply.lhs.tok.position, source.index("-"))
        self.assertEqual(multiply.lhs.lhs.tok.position, source.index("+"))
        self.assertEqual(multiply.rhs.tok.text, "3")
        for source, position in [('int main(void){1=2;}', 15), ('int main(void){(1+2)=3;}', 17),
                                 ('int main(void){int a; -a=3;}', 22), ('int main(void){(2>1)=3;}', 17)]:
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
            ('int main(void){int i; i=0; while(i<10) {i=i+1;} return i;}', 10),
            ('int main(void){while(0) return 9; return 3;}', 3),
            ('int main(void){while(-2) return 7;}', 7),
            ('int main(void){int i, sum; i=3; sum=0; while(i) {sum=sum+i; i=i-1;} return sum;}', 6),
            ('int main(void){int i, j; i=0; while(i<3) {for(j=0;j<2;j=j+1); i=i+1;} return i+j;}', 5),
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
        result = compile_program('int main(void){while() ;}')
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
            ('int main(void){int i, j;  i=0; j=0; for(i=0;i<=10;i=i+1) j=i+j; return j; }', 55),
            ('int main(void){ for(;;) {return 3;} return 5; }', 3),
            ('int main(void){int i;  i=4; for(;i<4;i=i+1) return 9; return i; }', 4),
            ('int main(void){int i;  i=0; for(;i<3;) i=i+1; return i; }', 3),
            ('int main(void){int i;  i=0; for(;;i=i+1) if(i==4) return i; }', 4),
            ('int main(void){int sum, i, j;  sum=0; for(i=0;i<3;i=i+1) for(j=0;j<2;j=j+1) sum=sum+1; return sum; }', 6),
            ('int main(void){int i;  for(i=0;i<3;i=i+1); return i; }', 3),
            ('int main(void){int format;  format=7; return format; }', 7),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assert_program_returns(source, expected)
        program = parse_body("for(;;) return 3;")
        node = program.body.body[0]
        self.assertEqual(grammar_tree(node.init), Node("BLOCK"))
        self.assertIsNone(node.cond)
        self.assertIsNone(node.inc)
        self.assertEqual(instruction_assembly(CodeGenerator().generate([program]) + "\n"), PROLOGUE + "  sub $0, %rsp\n"
                         ".L.begin.1:\n  mov $3, %rax\n  jmp .L.return.main\n"
                         ".L..1:\n  jmp .L.begin.1\n.L..0:\n" + EPILOGUE)
        for source, position, message in [
            ('int main(void){for 1;}', 19, "expected '('"),
            ('int main(void){for(1 2;3) ;}', 21, "expected ';'"),
            ('int main(void){for(;1 2;) ;}', 22, "expected ';'"),
            ('int main(void){for(;;1 2) ;}', 23, "expected ')'"),
        ]:
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stderr, "-:1: " + source + "\n" + " " * (position + len("-:1: ")) + "^ " + message + "\n")

    def test_if_tree_and_labels(self):
        program = parse_body("if(1) if(0) return 2; else return 3;")
        outer = program.body.body[0]
        self.assertEqual(outer.kind, "IF")
        self.assertEqual(grammar_tree(outer.cond), Node("NUM", value=1))
        self.assertIsNone(outer.els)
        self.assertEqual(grammar_tree(outer.then.els), Node("RETURN", lhs=Node("NUM", value=3)))
        assembly = CodeGenerator().generate([program])
        for label in (".L.else.1:", ".L.end.1:", ".L.else.2:", ".L.end.2:"):
            self.assertEqual(assembly.count(label), 1)

    def test_null_statements(self):
        program = parse(tokenize('int main(void){ ;;; return 5; }'))[0]
        self.assertEqual(grammar_tree(program.body), Node("BLOCK", body=[
            Node("BLOCK"), Node("BLOCK"), Node("BLOCK"),
            Node("RETURN", lhs=Node("NUM", value=5)),
        ]))
        for source in ['int main(void){ ;;; return 5; }', 'int main(void){ {}; return 5;; }', 'int main(void){ return 5; ;;; }']:
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n"
                                 "  mov $5, %rax\n  jmp .L.return.main\n" + EPILOGUE)
        # A program containing only null statements does not set a return value.
        result = compile_program('int main(void){;;;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n" + EPILOGUE)

    def test_nested_block_tree(self):
        program = parse(tokenize('int main(void){ {1;} return 2; }'))[0]
        self.assertEqual(grammar_tree(program.body), Node("BLOCK", body=[
            Node("BLOCK", body=[Node("EXPR_STMT", lhs=Node("NUM", value=1))]),
            Node("RETURN", lhs=Node("NUM", value=2)),
        ]))
        result = compile_program('int main(void){ {1;} return 2; }')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $0, %rsp\n"
                         "  mov $1, %rax\n  mov $2, %rax\n  jmp .L.return.main\n" + EPILOGUE)

    def test_function_definitions(self):
        source = "int ret32();int main(void){return ret32();} int ret32(void){return 32;}"
        self.assert_program_returns(source, 32)
        self.assert_program_returns("int f(void){int x=4; return x;} int main(void){int x=3; return f()+x;}", 7)
        assembly = compile_program(source).stdout
        self.assertIn(".L.return.main:", assembly)
        self.assertIn(".L.return.ret32:", assembly)
        self.assertEqual(compile_program("{return 1;}").returncode, 1)
        self.assertEqual(compile_program("int main(void){} return 3;").returncode, 1)
        self.assertEqual(compile_program("int main(void){return 1}").returncode, 1)
        self.assertEqual(compile_program("").stdout, '.file 1 "-"\n')
        self.assertEqual(parse(tokenize("")), [])

    def test_return_tree(self):
        program = parse_body("return 1+2; 3;")
        self.assertEqual(grammar_tree(program.body.body), [
            Node("RETURN", lhs=Node("+", Node("NUM", value=1), Node("NUM", value=2))),
            Node("EXPR_STMT", lhs=Node("NUM", value=3)),
        ])

    def test_local_objects_and_stack_layout(self):
        program = parse_body("int foo=3; int bar=5; return foo+bar;")
        self.assertEqual([var.name for var in program.locals], ["bar", "foo"])
        bar, foo = program.locals
        self.assertIs(grammar_tree(program.body.body[0].body[0].lhs).lhs.var, foo)
        expression = grammar_tree(program.body.body[2].lhs)
        self.assertIs(expression.lhs.var, foo)
        self.assertIs(grammar_tree(program.body.body[1].body[0].lhs).lhs.var, bar)
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
        self.assertEqual(grammar_tree(statements.body.body), [
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
                self.assertEqual(grammar_tree(parse_body(source)), Obj("main", body=Node("BLOCK"), is_function=True,
                                                        is_definition=True))
                result = compile_program('int main(void){' + source + "}")
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
            ('- -5;', Node("NEG", lhs=Node("NEG", lhs=five))),
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
                self.assertEqual(grammar_tree(statements.body.body), [Node("EXPR_STMT", lhs=expected)])
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
                result = compile_program('int main(void){' + source + "}")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                stack_size = 16 if source in ("int a; a=3; a;", "int z; z=5;") else 0
                self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + f"  sub ${stack_size}, %rsp\n" + instructions + EPILOGUE)

    def test_executable_exit_status(self):
        # All current upstream examples and earlier arithmetic/control regressions.
        cases = [
            ('int main(void){ return 0; }', 0),
            ('int main(void){ return 42; }', 42),
            ('int main(void){ return 5+20-4; }', 21),
            ('int main(void){ return  12 + 34 - 5 ; }', 41),
            ('int main(void){ return 5+6*7; }', 47),
            ('int main(void){ return 5*(9-6); }', 15),
            ('int main(void){ return (3+5)/2; }', 4),
            ('int main(void){ return -10+20; }', 10),
            ('int main(void){ return - -10; }', 10),
            ('int main(void){ return - - +10; }', 10),
            ('int main(void){ return 0==1; }', 0),
            ('int main(void){ return 42==42; }', 1),
            ('int main(void){ return 0!=1; }', 1),
            ('int main(void){ return 42!=42; }', 0),
            ('int main(void){ return 0<1; }', 1),
            ('int main(void){ return 1<1; }', 0),
            ('int main(void){ return 2<1; }', 0),
            ('int main(void){ return 0<=1; }', 1),
            ('int main(void){ return 1<=1; }', 1),
            ('int main(void){ return 2<=1; }', 0),
            ('int main(void){ return 1>0; }', 1),
            ('int main(void){ return 1>1; }', 0),
            ('int main(void){ return 1>2; }', 0),
            ('int main(void){ return 1>=0; }', 1),
            ('int main(void){ return 1>=1; }', 1),
            ('int main(void){ return 1>=2; }', 0),
            ('int main(void){ int a; a=3; return a; }', 3),
            ('int main(void){ int a=3; return a; }', 3),
            ('int main(void){ int a=3; int z=5; return a+z; }', 8),
            ('int main(void){ int a; int b; a=b=3; return a+b; }', 6),
            ('int main(void){ int foo=3; return foo; }', 3),
            ('int main(void){ int foo123=3; int bar=5; return foo123+bar; }', 8),
            ('int main(void){ return 1; 2; 3; }', 1),
            ('int main(void){ 1; return 2; 3; }', 2),
            ('int main(void){ 1; 2; return 3; }', 3),
            ('int main(void){ {1; {2;} return 3;} }', 3),
            ('int main(void){ ;;; return 5; }', 5),
            ('int main(void){ if (0) return 2; return 3; }', 3),
            ('int main(void){ if (1-1) return 2; return 3; }', 3),
            ('int main(void){ if (1) return 2; return 3; }', 2),
            ('int main(void){ if (2-1) return 2; return 3; }', 2),
            ('int main(void){ if (0) { 1; 2; return 3; } else { return 4; } }', 4),
            ('int main(void){ if (1) { 1; 2; return 3; } else { return 4; } }', 3),
            ('int main(void){ int i=0; int j=0; for (i=0; i<=10; i=i+1) j=i+j; return j; }', 55),
            ('int main(void){ for (;;) return 3; return 5; }', 3),
            ('int main(void){ int i=0; while(i<10) i=i+1; return i; }', 10),
            ('int main(void){ int i=0; int j=0; while(i<=10) {j=i+j; i=i+1;} return j; }', 55),
            ('int main(void){ int x=3; return *&x; }', 3),
            ('int main(void){ int x=3; int *y=&x; int **z=&y; return **z; }', 3),
            ('int main(void){ int x=3; int y=5; return *(&x+1); }', 5),
            ('int main(void){ int x=3; int y=5; return *(&y-1); }', 3),
            ('int main(void){ int x=3; int y=5; return *(&x-(-1)); }', 5),
            ('int main(void){ int x=3; int *y=&x; *y=5; return x; }', 5),
            ('int main(void){ int x=3; int y=5; *(&x+1)=7; return y; }', 7),
            ('int main(void){ int x=3; int y=5; *(&y-2+1)=7; return x; }', 7),
            ('int main(void){ int x=3; return (&x+2)-&x+3; }', 5),
            ('int main(void){ int x, y; x=3; y=5; return x+y; }', 8),
            ('int main(void){ int x=3, y=5; return x+y; }', 8),
            ('int main(void){if (0) return 2; return 3;}', 3),
            ('int main(void){if (1-1) return 2; return 3;}', 3),
            ('int main(void){if (1) return 2; return 3;}', 2),
            ('int main(void){if (2-1) return 2; return 3;}', 2),
            ('int main(void){if (0) {1; 2; return 3;} else {return 4;}}', 4),
            ('int main(void){if (1) {1; 2; return 3;} else {return 4;}}', 3),
            ('int main(void){if(-3) return 7; else return 9;}', 7),
            ('int main(void){if(256) return 7; return 9;}', 7),
            ('int main(void){int a; a=0; if(1) a=3; else a=8; return a;}', 3),
            ('int main(void){int a; a=0; if(0) a=3; else a=8; return a;}', 8),
            ('int main(void){if(1) if(0) return 2; else return 3; return 4;}', 3),
            ('int main(void){if(0) if(1) return 2; else return 3; return 4;}', 4),
            ('int main(void){if(0) {if(1) return 2;} else return 3;}', 3),
            ('int main(void){if(0) return 1; else if(0) return 2; else return 3;}', 3),
            ('int main(void){int a; a=0; if(a=5) a=a+2; if(a==7) a=a*2; return a;}', 14),
            ('int main(void){if(1); else return 2; return 3;}', 3),
            ('int main(void){int ifx, elsewhere; ifx=3; elsewhere=4; if(ifx<elsewhere) return 8; return 9;}', 8),
            ('int main(void){;;; return 5;}', 5),
            ('int main(void){1;;}', 1),
            ('int main(void){int a; a=3;; {;; a=a+2;;}; return a;;}', 5),
            ('int main(void){return 7;;;;}', 7),
            ('int main(void){{1; {2;} return 3;}}', 3),
            ('int main(void){{} return 7;}', 7),
            ('int main(void){{{return 5;}} return 9;}', 5),
            ('int main(void){int a, b; a=1; {a=4; b=3;} return a+b;}', 7),
            ('int main(void){int a; a=2; {a=a*3; {a=a+4;}} return a;}', 10),
            ('int main(void){{{{}}} return 8;}', 8),
            ('int main(void){return 0;}', 0),
            ('int main(void){return 42;}', 42),
            ('int main(void){return 5+20-4;}', 21),
            ('int main(void){return  12 + 34 - 5 ;}', 41),
            ('int main(void){return 5+6*7;}', 47),
            ('int main(void){return 5*(9-6);}', 15),
            ('int main(void){return (3+5)/2;}', 4),
            ('int main(void){return -10+20;}', 10),
            ('int main(void){return - -10;}', 10),
            ('int main(void){return - - +10;}', 10),
            ('int main(void){return 0==1;}', 0),
            ('int main(void){return 42==42;}', 1),
            ('int main(void){return 0!=1;}', 1),
            ('int main(void){return 42!=42;}', 0),
            ('int main(void){return 0<1;}', 1),
            ('int main(void){return 1<1;}', 0),
            ('int main(void){return 2<1;}', 0),
            ('int main(void){return 0<=1;}', 1),
            ('int main(void){return 1<=1;}', 1),
            ('int main(void){return 2<=1;}', 0),
            ('int main(void){return 1>0;}', 1),
            ('int main(void){return 1>1;}', 0),
            ('int main(void){return 1>2;}', 0),
            ('int main(void){return 1>=0;}', 1),
            ('int main(void){return 1>=1;}', 1),
            ('int main(void){return 1>=2;}', 0),
            ('int main(void){int a; a=3; return a;}', 3),
            ('int main(void){int a, z; a=3; z=5; return a+z;}', 8),
            ('int main(void){int a, b; a=b=3; return a+b;}', 6),
            ('int main(void){int foo; foo=3; return foo;}', 3),
            ('int main(void){int foo123, bar; foo123=3; bar=5; return foo123+bar;}', 8),
            ('int main(void){return 1; 2; 3;}', 1),
            ('int main(void){1; return 2; 3;}', 2),
            ('int main(void){1; 2; return 3;}', 3),
            ('int main(void){return 1; return 2;}', 1),
            ('int main(void){int foo; foo=7; return (foo+5)*(foo-2); foo=99;}', 60),
            ('int main(void){int total; return total=9; total=0;}', 9),
            ('int main(void){int returnx, return_, Return; returnx=3; return_=4; Return=5; return returnx+return_+Return;}', 12),
            ('int main(void){return(3+4);}', 7),
            ('int main(void){return -7;}', 249),
            ('int main(void){int foo; foo=3; foo;}', 3),
            ('int main(void){int foo123, bar; foo123=3; bar=5; foo123+bar;}', 8),
            ('int main(void){int foo, foo123; foo=3; foo123=7; foo+foo123;}', 10),
            ('int main(void){int Foo, foo; Foo=3; foo=7; Foo+foo;}', 10),
            ('int main(void){int _, _value1; _=2; _value1=5; _+_value1;}', 7),
            ('int main(void){int total, left, right; total=left=right=4; total+left+right;}', 12),
            ('int main(void){int count; count=3; count=count+4; count;}', 7),
            ('int main(void){int alpha, beta, gamma; alpha=1; beta=2; gamma=3; alpha+beta+gamma;}', 6),
            ('int main(void){int a; a=3; a;}', 3),
            ('int main(void){int a, z; a=3; z=5; a+z;}', 8),
            ('int main(void){int a, b; a=b=3; a+b;}', 6),
            ('int main(void){int a; a=1; a=a+2; a;}', 3),
            ('int main(void){int a, b; a=4; b=7; a=9; b;}', 7),
            ('int main(void){int a; a=5==5; a;}', 1),
            ('int main(void){int a; a=3; (a=7)+2;}', 9),
            ('int main(void){int a, b; a=-(3+4); b=2; a/b;}', 253),
            ('int main(void){int a; (a)=6; a;}', 6),
            ('int main(void){int a; a=65536*65536; a/65536/65536;}', 0),
            ('int main(void){int a, z; a=2; z=8; (a+z)*(z-a); a+z;}', 10),
            ('int main(void){1; 2; 3;}', 3),
            ('int main(void){42; 0;}', 0),
            ('int main(void){1+2; 3*(4+5); (10-3)/2;}', 3),
            ('int main(void){5<6; -7;}', 249),
            ('int main(void){10;\n 20+22;\n}', 42),
            ('int main(void){0;}', 0),
            ('int main(void){42;}', 42),
            ('int main(void){5+20-4;}', 21),
            ('int main(void){ 12 + 34 - 5 ;}', 41),
            ('int main(void){5+6*7;}', 47),
            ('int main(void){5*(9-6);}', 15),
            ('int main(void){(3+5)/2;}', 4),
            ('int main(void){255;}', 255),
            ('int main(void){256;}', 0),
            ('int main(void){ 0042 ;}', 34),
            ('int main(void){2147483647;}', 255),
            ('int main(void){10-3-2;}', 5),
            ('int main(void){0-1;}', 255),
            ('int main(void){255+2;}', 1),
            ('int main(void){5+ 20-4;}', 21),
            ('int main(void){5 +20-4;}', 21),
            ('int main(void){\t12\n+\r34\x0b-\x0c5 ;}', 41),
            ('int main(void){1\u2003+\u20032;}', 3),
            ('int main(void){1+2147483647;}', 0),
            ('int main(void){0-2147483647-1;}', 0),
            ('int main(void){(5+6)*7;}', 77),
            ('int main(void){20/3;}', 6),
            ('int main(void){20/2/2;}', 5),
            ('int main(void){20/(2/2);}', 20),
            ('int main(void){24/3*2;}', 16),
            ('int main(void){24/(3*2);}', 4),
            ('int main(void){20-3*4+8/2;}', 12),
            ('int main(void){((2+3)*(4+(8/2)));}', 40),
            ('int main(void){((42));}', 42),
            ('int main(void){(0-7)/2;}', 253),
            ('int main(void){7/(0-2);}', 253),
            ('int main(void){(0-7)/(0-2);}', 3),
            ('int main(void){(0-3)*4;}', 244),
            ('int main(void){100/(2+3*(4-2));}', 12),
            ('int main(void){65536*65536/65536/65536;}', 0),
            ('int main(void){-10+20;}', 10),
            ('int main(void){- -10;}', 10),
            ('int main(void){- - +10;}', 10),
            ('int main(void){-1;}', 255),
            ('int main(void){+42;}', 42),
            ('int main(void){1+-2;}', 255),
            ('int main(void){1- -2;}', 3),
            ('int main(void){1+ +2;}', 3),
            ('int main(void){1 + +2;}', 3),
            ('int main(void){-(3+4)*2;}', 242),
            ('int main(void){2*-(3+4);}', 242),
            ('int main(void){-20/3;}', 250),
            ('int main(void){20/-3;}', 250),
            ('int main(void){-20/-3;}', 6),
            ('int main(void){3*-4+15;}', 3),
            ('int main(void){-(-(-5));}', 251),
            ('int main(void){-2147483647-1;}', 0),
            ('int main(void){0==1;}', 0),
            ('int main(void){42==42;}', 1),
            ('int main(void){0!=1;}', 1),
            ('int main(void){42!=42;}', 0),
            ('int main(void){0<1;}', 1),
            ('int main(void){1<1;}', 0),
            ('int main(void){2<1;}', 0),
            ('int main(void){0<=1;}', 1),
            ('int main(void){1<=1;}', 1),
            ('int main(void){2<=1;}', 0),
            ('int main(void){1>0;}', 1),
            ('int main(void){1>1;}', 0),
            ('int main(void){1>2;}', 0),
            ('int main(void){1>=0;}', 1),
            ('int main(void){1>=1;}', 1),
            ('int main(void){1>=2;}', 0),
            ('int main(void){-1<0;}', 1),
            ('int main(void){0>-1;}', 1),
            ('int main(void){-2<=-1;}', 1),
            ('int main(void){-1>=0;}', 0),
            ('int main(void){2147483647+1>0;}', 0),
            ('int main(void){5+6*7==47;}', 1),
            ('int main(void){5+6*7!=47;}', 0),
            ('int main(void){5==2+3;}', 1),
            ('int main(void){3<4==1;}', 1),
            ('int main(void){3==4<5;}', 0),
            ('int main(void){1<2<3;}', 1),
            ('int main(void){3>2>0;}', 1),
            ('int main(void){(3>2)+4;}', 5),
            ('int main(void){(5>=5)*7;}', 7),
            ('int main(void){1==1==1;}', 1),
            ('int main(void){2==2==2;}', 0),
            ('int main(void){' + "".join(f"int var{i}={i};" for i in range(30))
             + "+".join(f"var{i}" for i in range(30)) + ";}", 179),
            ('int main(void){' + "".join(f"int {chr(97+i)}={i+1};" for i in range(26))
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
                    arguments = ('int main(void){' + arguments[0] + "}",)
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
            ("1+18446744073709551616", "1+18446744073709551616\n  ^ integer must fit in unsigned 64 bits\n"),
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
                result = compile_program('int main(void){' + source + "}")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                if expected.startswith(source + "\n"):
                    expected = 'int main(void){' + source + "}\n" + " " * len('int main(void){') + expected[len(source) + 1:]
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
            ('int main(void){int; return 7;}', 7),
            ('int main(void){int x=3,y=x+2; return x+y;}', 8),
            ('int main(void){int x=3,*p=&x; *p=7; return x;}', 7),
            ('int main(void){int a,b; a=b=3; return a+b;}', 6),
            ('int main(void){int integer=5; return integer;}', 5),
            ('int main(void){int x=1; {int y=4; return x+y;}}', 5),
            ('int main(void){int x=1; {int x=4;} return x;}', 1),
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
            self.assertEqual(grammar_tree(statement.lhs).kind, "ASSIGN")
        program = parse_body("int a,b; a=b=3;")
        assignment = grammar_tree(program.body.body[1].lhs)
        self.assertEqual(assignment.kind, "ASSIGN")
        self.assertEqual(assignment.rhs.kind, "ASSIGN")
        result = compile_program('int main(void){int x; return 7;}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(instruction_assembly(result.stdout), PROLOGUE + "  sub $16, %rsp\n"
                         "  mov $7, %rax\n  jmp .L.return.main\n" + EPILOGUE)
        self.assertEqual(tokenize("int integer")[0].kind, "KEYWORD")
        self.assertEqual(tokenize("int integer")[1].kind, "IDENT")

    def test_declaration_errors(self):
        cases = [
            ('int main(void){x=3;}', 15, "undefined variable"),
            ('int main(void){return x; int x;}', 22, "undefined variable"),
            ('int main(void){int x=y;}', 21, "undefined variable"),
            ('int main(void){int 3;}', 19, "variable name omitted"),
            ('int main(void){int *;}', 20, "variable name omitted"),
            ('int main(void){int x y;}', 21, "expected ','"),
            ('int main(void){int x,;}', 21, "variable name omitted"),
            ('int main(void){int x=;}', 21, "expected an expression"),
            ('int main(void){return *1;}', 22, "invalid pointer dereference"),
            ('int main(void){int x=3; return *x;}', 31, "invalid pointer dereference"),
            ('int main(void){int x,y; return &x+&y;}', 33, "invalid operands"),
            ('int main(void){int x; return 1-&x;}', 30, "invalid operands"),
            ('int main(void){int x; (x+1)=3;}', 24, "not an lvalue"),
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
