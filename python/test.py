"""Run with python3 python/test.py on x86-64 Linux with GCC installed."""

from pathlib import Path
from dataclasses import replace
import argparse
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import time

from codegen import CodeGenerator
from common import CompileError, Node, Obj, Token, File, format_diagnostic
from parse import parse
from tokenizer import tokenize as tokenize_raw, tokenize_file, remove_backslash_newline, canonicalize_newline, convert_universal_chars
from preprocess import preprocess
from type import ty_int, ty_long, ty_short, ty_void
from main import add_default_include_paths
from unicode import is_ident1, is_ident2, char_width, display_width


COMPILER = Path(__file__).with_name("main.py")
PROLOGUE = "  .globl main\n  .text\nmain:\n  push %rbp\n  mov %rsp, %rbp\n"
EPILOGUE = "  mov $0, %rax\n.L.return.main:\n  mov %rbp, %rsp\n  pop %rbp\n  ret\n"


def tokenize(source):
    """Run the current token pipeline for parser tests and token snapshots."""
    return preprocess(tokenize_raw(source))


def compiler_command(*arguments):
    """Request assembly explicitly for existing compiler and driver fixtures."""
    return [sys.executable, str(COMPILER), "-S", "-o", "-", *arguments]


def compile_program(*arguments):
    """Feed in-memory source fixtures to the compiler through stdin."""
    if len(arguments) == 1:
        return subprocess.run(compiler_command("-"),
                              input=arguments[0], capture_output=True, text=True)
    return subprocess.run(
        compiler_command(*arguments),
        capture_output=True,
        text=True,
    )


def parse_body(source):
    """Parse a main function containing a statement-body fixture."""
    return next(obj for obj in parse(tokenize('int main(void){' + source + "}")) if obj.name == "main")


def instruction_assembly(assembly):
    """Keep function snapshots independent of debug metadata and global data."""
    lines = [line for line in assembly.splitlines(keepends=True)
             if not line.lstrip().startswith((".file ", ".loc "))]
    for index, line in enumerate(lines):
        if line.strip() == ".text":
            return "".join(lines[index - 1:])
    return "".join(lines)


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
    def test_gnu_line_markers(self):
        self.assert_program_returns('# 41 "virtual.c" 2 3\nint main(void){return __LINE__+(__FILE__[0]!=118);}', 42)
        self.assert_program_returns('# 41\nint main(void){return __LINE__;}', 42)
        result = compile_program('# 41L "virtual.c"\nint main(void){return 0;}')
        self.assertEqual(result.returncode, 1)
        self.assertIn('invalid line marker', result.stderr)

    def test_line_directives(self):
        self.assert_program_returns('#line 41 "virtual.c"\nint main(void){return __LINE__;}', 42)
        tokens = tokenize('#line 40 "first.c"\na\n#line 10\nb\n')
        self.assertEqual([(t.text, t.line_no, t.filename) for t in tokens[:-1]], [('a', 41, 'first.c'), ('b', 11, 'first.c')])
        source = '#define MARK 41\n#define NAME "virtual.c"\n#line MARK NAME\nint main(void){return __LINE__+(__FILE__[0]!=118);}'
        self.assert_program_returns(source, 42)
        for marker, message in [('1L', 'invalid line marker'), ('1.0', 'invalid line marker'), ('abc', 'invalid line marker'), ('10 abc', 'filename expected')]:
            result = compile_program('#line ' + marker + '\nint main(void){return 0;}')
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)
        result = compile_program('#line 40 "virtual.c"\nint main(void){return missing;}')
        self.assertIn('-:41:', result.stderr)

    def test_unicode_diagnostic_columns(self):
        for character, width in [('a', 1), ('漢', 2), ('🍣', 2), ('\u0300', 0), ('\t', 0), ('\u303f', 1)]:
            self.assertEqual(char_width(character), width)
        self.assertEqual(display_width('漢a\u0300 '), 4)
        file = File('x.c', 1, '漢a\u0300 ?\n')
        self.assertEqual(format_diagnostic(file, 4, 'bad'), 'x.c:1: 漢a\u0300 ?\n' + ' ' * 11 + '^ bad')
        source = 'int main(void){/*漢字\u0300*/return missing;}'
        result = compile_program(source)
        self.assertEqual(result.returncode, 1)
        caret = result.stderr.splitlines()[1].index('^')
        self.assertEqual(caret, len('-:1: ') + source.index('missing') + 1)

    def test_anonymous_struct_designators(self):
        for source, expected in [
            ('int main(void){struct{struct{int a;struct{int b;};};int c;}x={1,2,3,.b=4,5};return x.a+x.b+x.c;}', 10),
            ('struct{struct{int a,b;};int c;}x={.b=12,30};int main(void){return x.a+x.b+x.c;}', 42),
            ('int main(void){union{struct{int a,b;};int c;}x={.b=42};return x.a+x.b;}', 42),
        ]:
            self.assert_program_returns(source, expected)

    def test_union_designated_initializers(self):
        for source, expected in [
            ('int main(void){union T{int a;char b[4];}x={.b[1]=42};return x.b[1]+x.b[0];}', 42),
            ('union T{int a;char b[4];}x={.b[2]=18};int main(void){return x.a==0x00120000;}', 1),
            ('union T{int a;}x[2]={};int main(void){return x[0].a+x[1].a;}', 0),
            ('int main(void){struct T{union{int a;int b;}u;}x={.u.b=42};return x.u.a;}', 42),
            ('int main(void){return ((union T{int a;int b;}){.b 42}).a;}', 42),
        ]:
            self.assert_program_returns(source, expected)

    def test_struct_designated_initializers(self):
        for source,expected in [
            ('int main(void){struct T{int a,b,c;}x={.c=30,.a=12};return x.a+x.b+x.c;}',42),
            ('struct T{int a,b;}g={1,2,.b=30,.a=12};int main(void){return g.a+g.b;}',42),
            ('int main(void){struct T{struct{int a,b;}t;int x[2];}v={.t.b=12,.x[1]=30};return v.t.a+v.t.b+v.x[0]+v.x[1];}',42),
            ('int main(void){struct T{int a,b;}x[]={[1].b=12,30};return x[1].b+x[2].a;}',42),
            ('int main(void){struct T{int a,b;}x={12,30};struct T y[]={x,[0].b=42};return y[0].a+y[0].b;}',42),
            ('int main(void){struct T{unsigned int a:6,b:4;}x={.a=42};return x.a+x.b;}',42),
            ('int main(void){return ((struct T{int a,b;}){.b 42}).b;}',42),
        ]:
            self.assert_program_returns(source,expected)
        for source,message in [
            ('struct T{int a;}x={.missing=1};','struct has no such member'),
            ('struct T{int a;}x={. 1=1};','expected a field designator'),
            ('int x[1]={[0].a=1};','field name not in struct or union initializer'),
        ]:
            result=compile_program('int main(void){'+source+'return 0;}')
            self.assertEqual(result.returncode,1)
            self.assertIn(message,result.stderr)

    def test_designators_without_equals(self):
        for source in ('int main(void){return ((int[10]){[3]42})[3];}',
                       'int x[]={[3]42};int main(void){return x[3]+x[0];}',
                       'int main(void){int x[2][3]={[1][2]42};return x[1][2];}',
                       'int main(void){int x[4]={[1]12,30};return x[1]+x[2];}'):
            self.assert_program_returns(source,42)

    def test_inferred_designated_array_bounds(self):
        for source,expected in [
            ('int main(void){char x[]={[10-3]=1,2,3};return sizeof(x);}',10),
            ('int main(void){char x[][2]={[8][1]=1,2};return sizeof(x);}',20),
            ('int x[]={[4]=42,[0]=1};int main(void){return sizeof(x)+x[4];}',62),
            ('int main(void){int x[]={[0]=12,[3]=30};return x[0]+x[3]+x[1]+x[2];}',42),
        ]:
            self.assert_program_returns(source,expected)

    def test_array_designated_initializers(self):
        for source,expected in [
            ('int main(void){int x[5]={1,[3]=20,21,[0]=2};return x[0]+x[3]+x[4];}',43),
            ('int x[6]={[4]=42};int main(void){return x[0]+x[3]+x[4]+x[5];}',42),
            ('int main(void){int x[2][3]={1,2,3,4,5,6,[0][1]=7,8,[1][0]=12};return x[0][0]+x[0][1]+x[0][2]+x[1][0]+x[1][1]+x[1][2];}',39),
            ('int main(void){return ((int[10]){[3]=42})[3];}',42),
        ]:
            self.assert_program_returns(source,expected)
        for initializer,message in [('[3]=1','array designator index exceeds array bounds'),('[-1]=1','array designator index exceeds array bounds'),('[0][0]=1','array index in non-array initializer')]:
            result=compile_program('int main(void){int x[3]={' + initializer + '};return 0;}')
            self.assertEqual(result.returncode,1)
            self.assertIn(message,result.stderr)

    def test_utf8_bom(self):
        result = subprocess.run([sys.executable,str(COMPILER),'-E','-o-','-'],input='\ufeffxyz\n',capture_output=True,text=True)
        self.assertEqual((result.returncode,result.stdout),(0,'xyz\n'))
        self.assert_program_returns('\ufeffint main(void){return 42;}\r\n',42)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'value.h'
            path.write_bytes(b'\xef\xbb\xbf#define VALUE 42\r\n')
            files=[]
            tokens=tokenize_file(path,files)
            self.assertEqual((tokens[0].text,tokens[0].position),('#',0))
            self.assertFalse(files[0].contents.startswith('\ufeff'))
            self.assert_program_returns(f'#include "{path}"\nint main(void){{return VALUE;}}',42)

    def test_mixed_width_string_concatenation(self):
        for spelling,size,expected in [('"α" u"β"',2,'αβ'.encode('utf-16-le')),('u"α" "β"',2,'αβ'.encode('utf-16-le')),('"🍣" U"β"',4,'🍣β'.encode('utf-32-le')),('L"α" L"β"',4,'αβ'.encode('utf-32-le'))]:
            token = tokenize(spelling)[0]
            self.assertEqual(token.str,expected+b'\0'*size)
            self.assertEqual(token.ty.size,len(expected)+size)
            self.assert_program_returns('int main(void){return (' + spelling + ')[0]=='+str(127843 if '🍣' in spelling else 945)+';}',1)
        self.assert_program_returns('int main(void){unsigned short x[]="α" u"β";return x[1]-904;}',42)
        self.assert_program_returns(r'int main(void){return ("\343\201\202" L"")[0]==0343;}',1)
        for spelling in ('u"a" U"b"','L"a" U"b"'):
            result = compile_program('int main(void){return sizeof(' + spelling + ');}')
            self.assertEqual(result.returncode,1)
            self.assertIn('unsupported non-standard concatenation',result.stderr)

    def test_dollar_identifiers(self):
        self.assertEqual([(t.kind,t.text) for t in tokenize_raw('$$$ a$b $0')[:-1]],[('IDENT',s) for s in ('$$$','a$b','$0')])
        self.assert_program_returns('int main(void){int $$$=42;return $$$;}',42)
        self.assert_program_returns('#define VALUE$ 42\nint main(void){return VALUE$;}',42)
        self.assert_program_returns('int x$=42;int main(void){return x$;}',42)
        self.assert_program_returns('int f$(int x){return x+1;}int main(void){return f$(41);}',42)

    def test_unicode_identifiers(self):
        for name in ('π','あβ0¾','🍣','a\u0300'):
            self.assert_program_returns('int main(void){int ' + name + '=42;return ' + name + ';}',42)
        self.assert_program_returns('int π=42;int main(void){return π;}',42)
        self.assert_program_returns(r'int main(void){int \u03c0=42;return π;}',42)
        self.assert_program_returns('#define 日本語 42\nint main(void){return 日本語;}',42)
        self.assertTrue(is_ident1('¾'))
        self.assertTrue(is_ident2('\u0300'))
        self.assertFalse(is_ident1('\u0300'))
        self.assertFalse(is_ident1('⟘'))
        result = compile_program('int main(void){int ⟘=1;return 0;}')
        self.assertEqual(result.returncode,1)
        self.assertIn('invalid token',result.stderr)

    def test_utf_encoding_predefined_macros(self):
        self.assertEqual([t.value for t in tokenize('__STDC_UTF_16__;__STDC_UTF_32__') if t.kind=='NUM'],[1,1])
        self.assert_program_returns('#if defined(__STDC_UTF_16__)&&__STDC_UTF_16__&&defined(__STDC_UTF_32__)&&__STDC_UTF_32__\nint main(void){return 42;}\n#else\n#error missing encoding macros\n#endif',42)
        result = subprocess.run([sys.executable,str(COMPILER),'-U__STDC_UTF_16__','-E','-'],input='__STDC_UTF_16__',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'__STDC_UTF_16__\n')

    def test_utf32_array_initializers(self):
        for prefix,spelling in [('U','unsigned int'),('L','int')]:
            self.assert_program_returns(f'int main(void){{{spelling} x[]={prefix}"🤔x";return x[0]==129300&&x[1]==120&&x[2]==0&&sizeof(x)==12;}}',1)
            self.assert_program_returns(f'{spelling} x[]={prefix}"β";int main(void){{return x[0]-904;}}',42)
        self.assert_program_returns(r'unsigned int x[]=U"\xffffffff";int main(void){return x[0]>>31;}',1)
        self.assert_program_returns(r'int x[]=L"\xffffffff";int main(void){return x[0]>>31;}',255)
        self.assert_program_returns('int main(void){unsigned int x[1]=U"βx";return sizeof(x)+38;}',42)

    def test_utf16_array_initializers(self):
        self.assert_program_returns('int main(void){unsigned short x[]=u"αβ";return x[0]==945&&x[1]==946&&x[2]==0&&sizeof(x)==6;}',1)
        self.assert_program_returns('unsigned short x[]=u"🍣";int main(void){return x[0]==0xd83c&&x[1]==0xdf63&&x[2]==0&&sizeof(x)==6;}',1)
        self.assert_program_returns('int main(void){unsigned short x[2]=u"abc";return x[0]+x[1];}',195)
        self.assert_program_returns('unsigned short x[5]=u"β";int main(void){return x[1]+x[4];}',0)
        source = 'unsigned short x[]=u"αβ";'
        self.assertEqual(next(var.init_data for var in parse(tokenize(source)) if var.name == 'x'),'αβ'.encode('utf-16-le')+b'\0\0')

    def test_wide_string_literals(self):
        for text in ('','abc','日本語','🍣'):
            token = tokenize('L"' + text + '"')[0]
            self.assertEqual(token.str,text.encode('utf-32-le')+b'\0\0\0\0')
            self.assertEqual((token.ty.base.size,token.ty.base.is_unsigned),(4,False))
        self.assert_program_returns('int main(void){return L"βb"[0]-904;}',42)
        self.assert_program_returns(r'int main(void){return (L"\xffffffff"[0]>>31)==-1;}',1)
        self.assertEqual(tokenize('#define S(x) #x\nS(L"a")')[0].str,b'L"a"\0')

    def test_utf32_string_literals(self):
        for text in ('','abc','日本語','🍣'):
            token = tokenize('U"' + text + '"')[0]
            data = text.encode('utf-32-le')+b'\0\0\0\0'
            self.assertEqual((token.str,token.ty.size,token.ty.base.is_unsigned),(data,len(data),True))
            self.assert_program_returns('int main(void){return sizeof(U"' + text + '");}',len(data))
        self.assert_program_returns('int main(void){return U"🍣b"[0]==127843&&U"🍣b"[1]==98&&U"🍣b"[2]==0;}',1)
        self.assert_program_returns(r'int main(void){return U"\xffffffff"[0]>>31;}',1)
        self.assertEqual(tokenize('#define S(x) #x\nS(U"a")')[0].str,b'U"a"\0')

    def test_utf16_string_literals(self):
        for text in ('','abc','日本語','🍣'):
            token = tokenize('u"' + text + '"')[0]
            data = text.encode('utf-16-le')+b'\0\0'
            self.assertEqual((token.str,token.ty.size,token.ty.base.size),(data,len(data),2))
            self.assert_program_returns('int main(void){return sizeof(u"' + text + '");}',len(data))
        self.assert_program_returns('int main(void){return u"βb"[0]==946&&u"βb"[1]==98&&u"βb"[2]==0;}',1)
        self.assert_program_returns('int main(void){return u"🍣"[0]==0xd83c&&u"🍣"[1]==0xdf63&&u"🍣"[2]==0;}',1)
        self.assertEqual(tokenize(r'u"\xffff"')[0].str,b'\xff\xff\0\0')
        self.assertEqual(tokenize('#define S(x) #x\nS(u"a")')[0].str,b'u"a"\0')

    def test_utf8_string_literals(self):
        token = tokenize('u8"α🌮"')[0]
        self.assertEqual((token.text,token.str,token.ty.base.size,token.ty.array_len),('u8"α🌮"','α🌮'.encode()+b'\0',1,7))
        self.assert_program_returns('int main(void){char s[]=u8"α🌮";return sizeof(s)+35;}',42)
        self.assert_program_returns('int main(void){return sizeof(u8"abc" "def");}',7)
        self.assertEqual(tokenize('#define S(x) #x\nS(u8"a")')[0].str,b'u8"a"\0')
        result = compile_program('int main(void){return sizeof(u8"unclosed);}')
        self.assertEqual(result.returncode,1)
        self.assertIn('unclosed string literal',result.stderr)

    def test_utf32_character_literals(self):
        for spelling,value in [("U'a'",97),("U'β'",946),("U'あ'",12354),("U'🍣'",127843)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.value,token.ty.kind,token.ty.size,token.ty.is_unsigned),(value,'INT',4,True))
            self.assert_program_returns(f'int main(void){{return {spelling}=={value};}}',1)
        self.assert_program_returns(r"int main(void){return (U'\xffffffff'>>31)+sizeof(U'a');}",5)
        self.assertEqual(tokenize("#define S(x) #x\nS(U'a')")[0].str,b"U'a'\0")

    def test_utf16_character_literals(self):
        for spelling,value in [("u'a'",97),("u'β'",946),("u'あ'",12354),("u'🍣'",62307),(r"u'\xffff'",65535),(r"u'\xffffffff'",65535)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.value,token.ty.kind,token.ty.size,token.ty.is_unsigned),(value,'SHORT',2,True))
            self.assert_program_returns(f'int main(void){{return {spelling}=={value};}}',1)
        self.assert_program_returns(r"int main(void){return (u'\xffff'>>15)+sizeof(u'a');}",3)
        self.assertEqual(tokenize("#define S(x) #x\nS(u'a')")[0].str,b"u'a'\0")

    def test_wide_unicode_character_literals(self):
        for spelling,value in [("L'β'",946),("L'あ'",12354),("L'🍣'",127843),(r"L'\xffffffff'",-1),(r"L'\x80'",128),("'β'",-78)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.value,token.ty.size),(value,4))
            self.assert_program_returns(f'int main(void){{return {spelling}=={value};}}',1)
        self.assert_program_returns(r"int main(void){return L'\u03B2'==946;}",1)

    def test_universal_character_escapes(self):
        self.assertEqual(convert_universal_chars(r'\u03B1\U0001F32E'), 'α🌮')
        self.assertEqual(convert_universal_chars(r'\\u03B1\u0000\u12xz'), r'\\u03B1\u0000\u12xz')
        for spelling, size in [(r'"\u03B1\u03B2\u03B3"',7), (r'"\u65E5\u672C\u8A9E"',10), (r'"\U0001F32E"',5)]:
            self.assert_program_returns('int main(void){return sizeof(' + spelling + ');}',size)
        self.assert_program_returns(r'int main(void){return "\U0001F32E"[0]==(char)240;}',1)
        self.assert_program_returns(r'int main(void){return sizeof("\\u03B1");}',7)
        for spelling in (r'"\uD800"',r'"\U00110000"'):
            result = compile_program('int main(void){return sizeof(' + spelling + ');}')
            self.assertEqual(result.returncode,1)
            self.assertIn('invalid Unicode code point',result.stderr)

    def test_canonical_newlines(self):
        self.assertEqual(canonicalize_newline('a\r\nb\rc\nd\r\r\n'),'a\nb\nc\nd\n\n')
        for newline in ('\n','\r\n','\r'):
            source = newline.join(('#define VALUE \\', '42', 'int main(void){return VALUE;}', ''))
            self.assert_program_returns(source,42)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'main.c'
                path.write_bytes(source.encode())
                files = []
                tokens = tokenize_file(path,files)
                self.assertNotIn('\r', files[0].contents)
                self.assertEqual(next(t.line_no for t in tokens if t.text == 'int'),3)
        result = compile_program('int main(void){\rreturn missing;\r}')
        self.assertEqual(result.returncode,1)
        self.assertIn('-:2: return missing;',result.stderr)

    def test_counter_macro(self):
        self.assertEqual([token.value for token in tokenize('__COUNTER__;__COUNTER__;__COUNTER__') if token.kind == 'NUM'],[0,1,2])
        self.assertEqual(tokenize('__COUNTER__')[0].value,0)
        self.assert_program_returns('#define C __COUNTER__\nint main(void){return C+C+41;}',42)
        source = '#if 0\n__COUNTER__\n#endif\n#if __COUNTER__==0\nint main(void){return __COUNTER__+41;}\n#endif'
        self.assert_program_returns(source,42)
        self.assert_program_returns('#define P(a,b) a##b\n#define Q(a,b) P(a,b)\nint main(void){int x0=42;return Q(x,__COUNTER__);}',42)

    def test_date_and_time_macros(self):
        fixed = time.struct_time((2020,1,7,3,4,5,1,7,-1))
        with patch('preprocess.time.localtime', return_value=fixed):
            tokens = tokenize('__DATE__;__TIME__;__DATE__;__TIME__')
        self.assertEqual([t.str for t in tokens if t.kind == 'STR'],
                         [b'Jan  7 2020\0',b'03:04:05\0'] * 2)
        self.assert_program_returns('int main(void){return sizeof(__DATE__)+sizeof(__TIME__)+21;}',42)
        result = subprocess.run([sys.executable,str(COMPILER),'-D__DATE__="fixed"','-E','-'],input='__DATE__',capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout,'"fixed"\n')

    def test_anonymous_aggregate_members(self):
        for source, expected in [
            ('int main(void){struct T{char pad;struct{int a;union{int b,c;};};}x={1,{12,{30}}};return x.a+x.c;}',42),
            ('int main(void){union T{struct{unsigned char a,b,c,d;};long e;}x;x.e=0xdeadbeef;return x.c;}',173),
            ('struct T{struct{int a;};int b;}g={{12},30};int main(void){struct T*p=&g;return p->a+p->b;}',42),
            ('int main(void){struct T{struct{int a:10;};}x={{2}};return x.a+=40;}',42),
        ]:
            self.assert_program_returns(source,expected)
        result = compile_program('int main(void){struct T{struct{int a;};}x;return x.missing;}')
        self.assertEqual(result.returncode,1)
        self.assertIn('no such member',result.stderr)

    def test_main_implicit_zero(self):
        for source in ('int main(void){}', 'int main(void){42;}',
                       'int f(void){return 42;}int main(void){f();}'):
            self.assert_program_returns(source, 0)
        self.assert_program_returns('int main(void){return 42;}', 42)
        assembly = compile_program('int f(void){}int main(void){return 42;}').stdout
        self.assertIn('  mov $0, %rax\n.L.return.main:\n', assembly)
        self.assertNotIn('  mov $0, %rax\n.L.return.f:\n', assembly)

    def test_large_array_variable_alignment(self):
        for size in (16,17,100,101):
            self.assert_program_returns(f'int main(void){{char x[{size}];return (unsigned long)&x%16;}}',0)
        program = parse(tokenize('int main(void){_Alignas(32)char x[17];return 0;}'))
        CodeGenerator().generate(program)
        function = next(var for var in program if var.is_function)
        self.assertEqual(next(var.offset for var in function.locals if var.name == 'x') % 32, 0)
        self.assert_program_returns('int main(void){char x[17];return _Alignof(x);}',1)
        assembly = compile_program('char x[17];').stdout
        self.assertIn('  .globl x\n  .align 16\n', assembly)
        self.assertIn('  .globl x\n  .align 1\n', compile_program('char x[15];').stdout)

    def test_ignored_driver_flags(self):
        options = ['-O','-O2','-Wall','-Werror','-g','-g3','-std=c11',
                   '-ffreestanding','-fno-builtin','-fno-omit-frame-pointer',
                   '-fno-stack-protector','-fno-strict-aliasing','-m64','-mno-red-zone','-w']
        source = 'int main(void){return 42;}'
        result = subprocess.run(compiler_command(*options, '-'), input=source, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, compile_program(source).stdout)
        result = subprocess.run(compiler_command('-funrecognized', '-'), input=source, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('unknown argument: -funrecognized', result.stderr)

    def test_buffered_assembly_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'main.c', Path(directory) / 'main.s'
            source.write_text('int main(void){return &1;}')
            output.write_text('existing assembly\n')
            result = subprocess.run([sys.executable, str(COMPILER), '-S', '-o', str(output), str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('not an lvalue', result.stderr)
            self.assertEqual(output.read_text(), 'existing assembly\n')
            output.unlink()
            result = subprocess.run([sys.executable, str(COMPILER), '-S', '-o', str(output), str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(output.exists())
            source.write_text('int main(void){return 42;}')
            result = subprocess.run([sys.executable, str(COMPILER), '-S', '-o', str(output), str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('  mov $42, %rax\n', output.read_text())
        failed = compile_program('int main(void){return &1;}')
        self.assertEqual(failed.stdout, '')

    def test_bitfield_address_rejection(self):
        for expression in ('&x.a', '&(x.a)', '&p->a'):
            result = compile_program('int main(void){struct T{int a:3;int b;}x;struct T*p=&x;' + expression + ';return 0;}')
            self.assertEqual(result.returncode, 1)
            self.assertIn('cannot take address of bitfield', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        self.assert_program_returns('int main(void){struct T{int a:3;int b;}x={1,42};int*p=&x.b;return *p;}', 42)

    def test_zero_width_bitfield_alignment(self):
        for members, size in [('int a:3;int:0;int c:5;',8), ('int a:3;int:0;',4),
                              ('char a;long:0;char b;',16), ('int:0;int c:5;',4)]:
            self.assert_program_returns('int main(void){return sizeof(struct T{' + members + '});}', size)
        ty = next(var.ty for var in parse_body('struct T{int a:3;int:0;int b:5;}x;return 0;').locals if var.name == 'x')
        self.assertIsNone(ty.members[1].name)
        self.assertEqual((ty.members[2].offset,ty.members[2].bit_offset), (4,0))

    def test_bitfield_compound_assignments(self):
        for expression, expected in [('x.b++', 2), ('++x.b', 3), ('x.b+=40', 42),
                                     ('x.b*=21', 42), ('x.b=42', 42)]:
            self.assert_program_returns('int main(void){struct T{int a:10,b:10,c:10;}x={1,2,3};return ' + expression + ';}', expected)
        self.assert_program_returns('int main(void){struct T{int a:10,b:10;}x[2]={{1,2},{3,4}};int i=0;x[i++].b+=40;return i+x[0].a+x[0].b;}', 44)
        self.assert_program_returns('int main(void){struct T{int a:10,b:10;}x={1,2};x.b<<=2;return x.a+x.b;}', 9)

    def test_global_bitfield_initializers(self):
        source = 'struct T{char a;unsigned int b:5,c:10;}g={1,31,42},z={};int main(void){return g.c+z.a+z.b+z.c;}'
        self.assert_program_returns(source, 42)
        program = parse(tokenize(source))
        g = next(var for var in program if var.name == 'g')
        self.assertEqual(g.init_data, ((1 | (31 << 8) | (42 << 13))).to_bytes(4,'little'))
        self.assert_program_returns('struct T{int a:3,b:4;}g={7,15};int main(void){return g.a+g.b;}', 254)
        self.assert_program_returns('struct T{unsigned int a:6,b:4;}g[2]={{42},{1,2}};int main(void){return g[0].a+g[0].b;}', 42)

    def test_bitfield_storage(self):
        for source, expected in [
            ('int main(void){struct T{unsigned int a:3,b:5;}x={7,19};x.a=2;return x.a+x.b;}', 21),
            ('int main(void){struct T{int a:2,b:3,c:3;}x={3,4,5};return x.a+x.b+x.c;}', 248),
            ('int main(void){return sizeof(struct T{int a:31,b:2;});}', 8),
            ('int main(void){struct T{short a;char b;unsigned int c:2,d:3,e:3;}x={1,2,3,4,5};return x.a+x.b+x.c+x.d+x.e;}', 15),
        ]:
            self.assert_program_returns(source, expected)
        function = parse_body('struct T{short a;char b;int c:2,d:3,e:3;}x;return 0;')
        ty = next(var.ty for var in function.locals if var.name == 'x')
        self.assertEqual([(m.offset,m.bit_offset,m.bit_width) for m in ty.members[-3:]], [(0,24,2),(0,26,3),(0,29,3)])
        self.assertEqual(ty.size, 4)
        assembly = compile_program('int main(void){struct T{int a:3;}x={7};return x.a;}').stdout
        self.assertIn('  sar $61, %rax\n', assembly)
        self.assertIn('  and %r9, %rax\n  or %rdi, %rax\n', assembly)

    def test_command_line_macro_undefinitions(self):
        for arguments, source, expected in [
            (['-Dfoo=bar', '-Ufoo'], 'foo', 'foo\n'),
            (['-Ufoo', '-Dfoo=42'], 'foo', '42\n'),
            (['-Dfoo=42', '-U', 'foo', '-Ufoo'], 'foo', 'foo\n'),
            (['-U__STDC__'], '#ifdef __STDC__\nbad\n#else\n42\n#endif', '42\n'),
            (['-Ufoo'], '#define foo 42\nfoo', '42\n'),
        ]:
            result = subprocess.run([sys.executable, str(COMPILER), '-E', *arguments, '-'], input=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)
        result = subprocess.run([sys.executable, str(COMPILER), '-', '-U'], input='', capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_command_line_macro_definitions(self):
        for arguments, source, expected in [
            (['-Dfoo'], 'foo', '1\n'), (['-D', 'foo=bar'], 'foo', 'bar\n'),
            (['-Dfoo='], 'foo', '\n'), (['-Dfoo=7', '-Dfoo=42'], 'foo', '42\n'),
            (['-D__STDC__=7'], '__STDC__', '7\n'),
            (['-DX=42'], '#if X==42\nX\n#endif\n', '42\n'),
        ]:
            result = subprocess.run([sys.executable, str(COMPILER), '-E', *arguments, '-'],
                                    input=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)
        with tempfile.TemporaryDirectory() as directory:
            source, executable = Path(directory) / 'main.c', Path(directory) / 'main'
            source.write_text('int main(void){return ANSWER;}')
            result = subprocess.run([sys.executable, str(COMPILER), '-DANSWER=42', '-o', str(executable), str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-', '-D'],
                                input='', capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_preprocessing_numbers(self):
        self.assertEqual([(t.kind, t.text) for t in tokenize_raw('0zz 4.57 0x1p-3 1e+2')[:-1]],
                         [('PP_NUM', text) for text in ('0zz', '4.57', '0x1p-3', '1e+2')])
        self.assert_program_returns('#define P(x,y) x##y\nint main(void){int f0zz=42;return P(f,0zz);}', 42)
        self.assert_program_returns('#define P(x,y) x##y\nint main(void){return P(4,.57)+0.5;}', 5)
        self.assert_program_returns('int main(void){return 0x1p3+34;}', 42)
        self.assert_program_returns('#if 0x1p3 == 8\nint main(void){return 42;}\n#endif', 42)
        self.assert_program_returns('#define UNUSED 0zz\n#if 0\n0zz\n#endif\nint main(void){return 42;}', 42)
        self.assertEqual(tokenize('08')[0].ty.kind, 'DOUBLE')
        self.assert_program_returns('int main(void){return 08;}', 8)
        for text in ('0zz', '0b2', '1e+', '3.4.5'):
            result = compile_program('int main(void){return ' + text + ';}')
            self.assertEqual(result.returncode, 1)
            self.assertIn('invalid numeric constant', result.stderr)

    def test_repeated_function_dereference(self):
        for expression in ('f', '*f', '***f', '**p', '*****p'):
            self.assert_program_returns('int f(int x){return x+1;}int main(void){int(*p)(int)=f;return (' + expression + ')(41);}', 42)
        plain = compile_program('int f(void);int main(void){return f();}').stdout
        repeated = compile_program('int f(void);int main(void){return (***f)();}').stdout
        self.assertEqual(instruction_assembly(plain), instruction_assembly(repeated))

    def test_va_copy(self):
        source = '#include <stdarg.h>\nint f(int n,...){va_list a,b;va_start(a,n);va_copy(b,a);int x=va_arg(a,int);int y=va_arg(a,int);int z=va_arg(b,int);va_end(a);va_end(b);return x+y+z;}int main(void){return f(2,12,18);}'
        self.assert_program_returns(source, 42)
        source = '#include <stdarg.h>\nint f(int n,...){va_list a,b;va_start(a,n);for(int i=0;i<6;i++)va_arg(a,int);va_copy(b,a);return va_arg(a,int)+va_arg(b,int);}int main(void){return f(7,1,2,3,4,5,6,21);}'
        self.assert_program_returns(source, 42)

    def test_variadic_stack_arguments(self):
        for spelling in ('int', 'double'):
            source = '#include <stdarg.h>\n' + f'double sum(int n,...){{va_list ap;va_start(ap,n);double s=0;for(int i=0;i<n;i++)s+=va_arg(ap,{spelling});va_end(ap);return s;}}int main(void){{return sum(10,1{ ".0" if spelling == "double" else ""},2,3,4,5,6,7,8,9,10);}}'
            if spelling == 'double':
                source = source.replace('2,3,4,5,6,7,8,9,10)', '2.0,3.0,4.0,5.0,6.0,7.0,8.0,9.0,10.0)')
            self.assert_program_returns(source, 55)
        source = '#include <stdarg.h>\nstruct T{long a,b,c;};int f(int n,...){va_list ap;va_start(ap,n);struct T x=va_arg(ap,struct T);return x.a+x.b+x.c;}int main(void){struct T x={12,15,15};return f(1,x);}'
        self.assert_program_returns(source, 42)
        assembly = compile_program('int f(int n,...){return n;}').stdout
        self.assertIn('  addq $16, ', assembly)

    def test_aggregate_return_definitions(self):
        for declaration, initializer, expression in [
            ('struct T{int a;double b;};', '{12,30}', 'f().a+f().b'),
            ('struct T{double a;long b;};', '{12,30}', 'f().a+f().b'),
            ('struct T{double a[2];};', '{{12,30}}', 'f().a[0]+f().a[1]'),
            ('struct T{char a[3];};', '{{12,15,15}}', 'f().a[0]+f().a[1]+f().a[2]'),
            ('struct T{long a,b,c;};', '{12,15,15}', 'f().a+f().b+f().c'),
            ('union T{long a;double b;};', '{42}', 'f().a'),
        ]:
            kind = declaration.split()[0]
            definition = declaration + f'{kind} T f(void){{return ({kind} T){initializer};}}'
            self.assert_program_returns(definition + f'int main(void){{return {expression};}}', 42)
            self.assert_program_returns(definition + 'int call(void);int main(void){return call();}', 42,
                                        declaration + f'{kind} T f(void);int call(void){{{kind} T x=f();return ' + expression.replace('f()', 'x') + ';}')
        self.assert_program_returns('struct T{long a,b,c;};struct T f(int a,int b,int c,int d,int e,int f,int g){return (struct T){a+b+c,d+e+f,g};}int main(void){struct T x=f(1,2,3,4,5,6,21);return x.a+x.b+x.c;}', 42)

    def test_aggregate_return_calls(self):
        for declaration, initializer, expression in [
            ('struct T{int a;double b;};', '{12,30}', 'f().a+f().b'),
            ('struct T{double a;long b;};', '{12,30}', 'f().a+f().b'),
            ('struct T{double a[2];};', '{{12,30}}', 'f().a[0]+f().a[1]'),
            ('struct T{char a[3];};', '{{12,15,15}}', 'f().a[0]+f().a[1]+f().a[2]'),
            ('struct T{long a,b,c;};', '{12,15,15}', 'f().a+f().b+f().c'),
            ('union T{long a;double b;};', '{42}', 'f().a'),
        ]:
            kind = declaration.split()[0]
            self.assert_program_returns(declaration + f'{kind} T f(void);int main(void){{return {expression};}}', 42,
                                        declaration + f'{kind} T f(void){{return ({kind} T){initializer};}}')
        source = 'struct T{long a,b,c;};struct T f(int,int,int,int,int,int,int);int main(void){struct T x=f(1,2,3,4,5,6,21);return x.a+x.b+x.c;}'
        self.assert_program_returns(source, 42, 'struct T{long a,b,c;};struct T f(int a,int b,int c,int d,int e,int f,int g){return (struct T){a+b+c,d+e+f,g};}')
        node = parse_body('struct T{int a;};struct T f(void);return f().a;').body.body[-1].lhs.lhs.lhs
        self.assertEqual(node.kind, 'FUNCALL')
        self.assertEqual(node.ret_buffer.ty.kind, 'STRUCT')

    def test_aggregate_parameter_definitions(self):
        for declaration, initializer, expression in [
            ('struct T{int a;double b;};', '{12,30}', 'x.a+x.b'),
            ('struct T{double a[2];};', '{{12,30}}', 'x.a[0]+x.a[1]'),
            ('struct T{char a[3];};', '{{12,15,15}}', 'x.a[0]+x.a[1]+x.a[2]'),
            ('struct T{long a,b,c;};', '{12,15,15}', 'x.a+x.b+x.c'),
            ('union T{long a;double b;};', '{42}', 'x.a'),
        ]:
            kind = declaration.split()[0]
            definition = declaration + f'int f({kind} T x){{return {expression};}}'
            caller = f'int main(void){{{kind} T x={initializer};return f(x);}}'
            self.assert_program_returns(definition + caller, 42)
            self.assert_program_returns(definition + 'int call(void);int main(void){return call();}', 42,
                                        declaration + f'int f({kind} T);' + caller.replace('main(void)', 'call(void)'))
        assembly = compile_program('struct T{char a[3];};int f(struct T x){return x.a[2];}').stdout
        self.assertIn('  shr $8, %rdi\n', assembly)

    def test_aggregate_argument_calls(self):
        for declaration, initializer, expression in [
            ('struct T{int a;double b;};', '{12,30}', 'x.a+x.b'),
            ('struct T{double a[2];};', '{{12,30}}', 'x.a[0]+x.a[1]'),
            ('struct T{char a[3];};', '{{12,15,15}}', 'x.a[0]+x.a[1]+x.a[2]'),
            ('struct T{long a,b,c;};', '{12,15,15}', 'x.a+x.b+x.c'),
            ('union T{long a;double b;};', '{42}', 'x.a'),
        ]:
            kind = declaration.split()[0]
            source = declaration + f'int f({kind} T);int main(void){{{kind} T x={initializer};return f(x);}}'
            helper = declaration + f'int f({kind} T x){{return {expression};}}'
            self.assert_program_returns(source, 42, helper)
        assembly = compile_program('struct T{long a,b,c;};int f(struct T);int main(void){struct T x={12,15,15};return f(x);}').stdout
        self.assertIn('  sub $24, %rsp\n', assembly)
        self.assertIn('  mov %r10b, 23(%rsp)\n', assembly)
        self.assertIn('  add $32, %rsp\n', assembly)

    def test_stack_parameter_definitions(self):
        for spelling in ('int', 'float', 'double'):
            parameters = ','.join(f'{spelling} x{i}' for i in range(1, 11))
            expression = '+'.join(f'x{i}' for i in range(1, 11))
            definition = f'{spelling} sum10({parameters}){{return {expression};}}'
            self.assert_program_returns(definition + 'int main(void){return sum10(1,2,3,4,5,6,7,8,9,10);}', 55)
            self.assert_program_returns(definition + 'int call(void);int main(void){return call();}', 55,
                                        f'{spelling} sum10({parameters});int call(void){{return sum10(1,2,3,4,5,6,7,8,9,10);}}')
        self.assert_program_returns('int f(char a,char b,char c,char d,char e,char f,char g,char h){return g/h;}int main(void){return f(1,2,3,4,5,6,40,10);}', 4)
        program = parse(tokenize('int f(int a,int b,int c,int d,int e,int f,int g,int h){int local=1;return g+h+local;}'))
        assembly = CodeGenerator().generate(program)
        function = next(obj for obj in program if obj.is_function)
        self.assertEqual([var.offset for var in function.params[-2:]], [16, 24])
        self.assertEqual(function.stack_size, 32)
        self.assertEqual(CodeGenerator().generate(program), assembly)
        self.assertIn('  lea 16(%rbp), %rax\n', assembly)

    def test_stack_argument_calls(self):
        for spelling in ('int', 'float', 'double'):
            parameters = ','.join(f'{spelling} x{i}' for i in range(1, 11))
            expression = '+'.join(f'x{i}' for i in range(1, 11))
            helper = f'{spelling} sum10({parameters}){{return {expression};}}'
            source = f'{spelling} sum10({parameters});int main(void){{return sum10(1,2,3,4,5,6,7,8,9,10);}}'
            self.assert_program_returns(source, 55, helper)
            self.assert_program_returns(source.replace('return sum10', 'return 1+sum10'), 56, helper)
        helper = '#include <stdarg.h>\nint sum(int n,...){va_list ap;va_start(ap,n);double result=0;for(int i=0;i<n;i++)result+=va_arg(ap,double);return result;}'
        self.assert_program_returns('int sum(int,...);int main(void){return sum(10,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.);}', 55, helper)
        self.assert_program_returns('int sum(int,...);int main(void){return 1+sum(10,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.);}', 56, helper)
        source = 'int sum(int,...);int main(void){return sum(10,1.,2.,3.,4.,5.,6.,7.,8.,9.,10.);}'
        assembly = compile_program(source).stdout
        self.assertIn('  mov $8, %rax\n  call *%r10\n  add $16, %rsp\n', assembly)
        helper = 'int mixed(int a,int b,int c,int d,int e,int f,int g,double x){return a+b+c+d+e+f+g+x;}'
        self.assert_program_returns('int mixed(int,int,int,int,int,int,int,double);int main(void){int x=0;mixed(0,0,0,0,0,0,x=1,x=2);return x;}', 2, helper)

    def test_complete_packaged_compiler_pipeline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'compiler.pyz'
            first, second = root / 'main.c', root / 'sum.c'
            executable = root / 'program'
            first.write_text('#include <stdbool.h>\nint sum(int,...);int main(void){bool ready=true;return sum(0,ready,41);}\n')
            second.write_text('''#include <stdarg.h>
int sum(int fixed,...){va_list ap;va_start(ap,fixed);
int x=va_arg(ap,int);int y=va_arg(ap,int);return x+y;}
''')
            built = subprocess.run([sys.executable, str(Path(__file__).with_name('build.py')), '-o', str(archive)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            compiled = subprocess.run([sys.executable, str(archive), '-o', str(executable),
                                       str(first), str(second)], cwd=root, capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            assembled = subprocess.run([sys.executable, str(archive), '-S', '-o', '-', str(first)],
                                       cwd=root, capture_output=True, text=True)
            self.assertEqual(assembled.returncode, 0, assembled.stderr)
            self.assertIn('  call *%r10\n', assembled.stdout)

    def test_va_arg_and_register_class(self):
        for typename, expected in (('int', 0), ('unsigned long', 0), ('char *', 0),
                                   ('int (*)(int)', 0), ('float', 1), ('double', 1),
                                   ('struct {int x;}', 2), ('void', 2)):
            self.assert_program_returns('int main(void){return __builtin_reg_class(' + typename + ');}', expected)
        self.assert_program_returns('''#include <stdarg.h>
int sum(int fixed,...){va_list ap;va_start(ap,fixed);
int first=va_arg(ap,int);int second=va_arg(ap,int);va_end(ap);return first+second;}
int main(void){return sum(0,7,35);}
''', 42)
        self.assert_program_returns('''#include <stdarg.h>
int mixed(int fixed,...){va_list ap;va_start(ap,fixed);
double value=va_arg(ap,double);int number=va_arg(ap,int);char *text=va_arg(ap,char *);
return value+number+text[0];}
int main(void){return mixed(0,1.5,37,"\\4");}
''', 42)
        result = compile_program('int main(void){return __builtin_reg_class(int;}')
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected ')'", result.stderr)

    def test_bundled_standard_headers(self):
        self.assert_program_returns('''#include <stdbool.h>
#include <stddef.h>
#include <stdalign.h>
#include <stdnoreturn.h>
#include <float.h>
#include <stdbool.h>
int main(void){bool ready=true;size_t size=sizeof(void*);alignas(16) int value;
return ready+false+size+sizeof(wchar_t)+alignof(long)+FLT_DIG+DBL_DIG;}
''', 42)
        self.assert_program_returns('''#include <stdarg.h>
int first(int fixed,...){va_list ap;va_start(ap,fixed);
int value=*(int*)((char*)ap->reg_save_area+ap->gp_offset);
va_end(ap);return value;}
int main(void){return first(0,42);}
''', 42)
        self.assert_program_returns('#include <float.h>\nint main(void){return FLT_MAX>1.0 && DBL_MAX>FLT_MAX;}\n', 1)
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'compiler.pyz'
            built = subprocess.run([sys.executable, str(Path(__file__).with_name('build.py')), '-o', str(archive)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            for header in Path(__file__).with_name('include').glob('*.h'):
                self.assertEqual((archive.parent / 'include' / header.name).read_bytes(), header.read_bytes())
            result = subprocess.run([sys.executable, str(archive), '-E', '-'],
                                    input='#include <stdbool.h>\nbool value=true;\n', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('_Bool value=1;', result.stdout)

    def test_wide_character_prefix(self):
        self.assert_program_returns("int main(void){return L'a';}", 97)
        self.assert_program_returns("int main(void){return sizeof(L'\\0');}", 4)
        self.assert_program_returns("int main(void){return L'\\xff'<0;}", 0)
        token = tokenize_raw("L'\\n'")[0]
        self.assertEqual((token.kind, token.text, token.value, token.position),
                         ('NUM', "L'\\n'", 10, 0))
        self.assertEqual(token.ty.kind, 'INT')
        result = compile_program("int main(void){return L'a;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn('unclosed char literal', result.stderr)

    def test_adjacent_string_literals(self):
        self.assert_program_returns('int main(void){return sizeof("abc" "def");}', 7)
        self.assert_program_returns('int main(void){return "ab" /*gap*/\n"cd"[2];}', 99)
        self.assert_program_returns('char s[]="a\\0" "b";int main(void){return sizeof(s)+s[2];}', 102)
        self.assert_program_returns('#define TAIL "def"\nint main(void){return "abc" TAIL[5];}\n', 102)
        tokens = tokenize('"\\x9" "0"\n')
        self.assertEqual(tokens[0].str, b'\t0\0')
        self.assertEqual(tokens[0].ty.array_len, 3)
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].text, '"\\x9"')
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                input='"abc" "def"\n', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '"abc"\n')

    def test_function_identifier(self):
        self.assert_program_returns('int main(void){return sizeof(__FUNCTION__);}', 5)
        self.assert_program_returns('char *answer(void){return __FUNCTION__;}int main(void){return answer()[5];}', 114)
        self.assert_program_returns('int main(void){return __func__==__FUNCTION__;}', 0)
        self.assert_program_returns('int main(void){int __FUNCTION__=42;return __FUNCTION__;}', 42)
        result = compile_program('char *name=__FUNCTION__;')
        self.assertEqual(result.returncode, 1)
        self.assertIn('undefined variable', result.stderr)

    def test_func_identifier(self):
        self.assert_program_returns('int main(void){return sizeof(__func__);}', 5)
        self.assert_program_returns('int answer(void){return __func__[0];}int main(void){return answer();}', 97)
        self.assert_program_returns('char *answer(void){return __func__;}int main(void){return answer()[5];}', 114)
        self.assert_program_returns('int main(void){int __func__=42;return __func__;}', 42)
        result = compile_program('char *name=__func__;')
        self.assertEqual(result.returncode, 1)
        self.assertIn('undefined variable', result.stderr)
        program = parse(tokenize('int main(void){return sizeof(__func__);}'))
        strings = [obj for obj in program if obj.init_data == b'main\0']
        self.assertEqual(len(strings), 2)
        self.assertEqual(strings[0].ty.kind, 'ARRAY')

    def test_variadic_macros(self):
        self.assert_program_returns('#define V(...) 42\nint main(void){return V();}\n', 42)
        self.assert_program_returns('#define V(...) __VA_ARGS__\nint main(void){return V() 42;}\n', 42)
        self.assert_program_returns('#define V(...) sum(__VA_ARGS__)\nint sum(int x,int y){return x+y;}int main(void){return V(7,35);}\n', 42)
        self.assert_program_returns('#define V(x,...) sum(x,__VA_ARGS__)\nint sum(int x,int y,int z){return x+y+z;}int main(void){return V(7,11,24);}\n', 42)
        self.assert_program_returns('#define V(x,...) x\nint main(void){return V(42);}\n', 42)
        self.assert_program_returns('#define V(...) __VA_ARGS__\n#define ADD(x,y) (x)+(y)\nint main(void){return V(ADD(7,35));}\n', 42)
        self.assertEqual(tokenize('#define V(...) #__VA_ARGS__\nV(1, 2)\n')[0].str, b'1, 2\0')
        result = compile_program('#define V(...,x) x\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected ')'", result.stderr)

    def test_file_and_line_macros(self):
        self.assert_program_returns('#define LINE __LINE__\n#define NEXT LINE\nint main(void){return NEXT;}\n', 3)
        self.assert_program_returns('#define LINE() __LINE__\n\nint main(void){return LINE();}\n', 3)
        tokens = tokenize('#define FIRST SECOND\n#define SECOND __LINE__\nFIRST\n')
        self.assertEqual(tokens[0].value, 3)
        self.assertEqual(tokenize('__FILE__')[0].str, b'-\0')
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / 'location.h'
            source = Path(directory) / 'main.c'
            header.write_text('char *header_file=__FILE__;\nint header_line=__LINE__;\n#define LINE() __LINE__\n#define FILE __FILE__\n')
            source.write_text('#include "location.h"\nchar *source_file=FILE;\n\nint main(void){return LINE()+header_line;}\n')
            result = subprocess.run([sys.executable, str(COMPILER), '-E', str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"' + str(header) + '"', result.stdout)
            self.assertIn('"' + str(source) + '"', result.stdout)
            self.assert_program_returns(result.stdout, 6)

    def test_predefined_macros(self):
        self.assert_program_returns('#if __STDC__ && defined(__x86_64__) && defined(__linux__)\nint main(void){return 42;}\n#else\n#error target\n#endif\n', 42)
        self.assert_program_returns('int main(void){return __SIZEOF_POINTER__==sizeof(void*) && __SIZEOF_LONG_DOUBLE__==sizeof(long double);}', 1)
        self.assert_program_returns('__SIZE_TYPE__ value=18446744073709551615UL;int main(void){return value>0;}', 1)
        self.assert_program_returns('__USER_LABEL_PREFIX__ int main(void){return __alignof__(long);}', 8)
        self.assert_program_returns('#undef __STDC__\n#if defined(__STDC__)\n#error removed\n#endif\n#define __STDC__ 7\nint main(void){return __STDC__;}\n', 7)
        self.assertEqual(tokenize('__STDC__')[0].value, 1)
        self.assertEqual(tokenize('#undef __STDC__\n__STDC__\n')[0].kind, 'IDENT')
        self.assertEqual(tokenize('__STDC__')[0].value, 1)

    def test_error_directive(self):
        for source in ('#error explanation\n', '#if 1\n#error\n#endif\n'):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn('^ error\n', result.stderr)
            self.assertEqual(result.stdout, '')
        self.assert_program_returns('#if 0\n#error unreachable\n#endif\nint main(void){return 42;}\n', 42)
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                input='#error stop\n', capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('^ error\n', result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / 'error.h'
            source = Path(directory) / 'main.c'
            header.write_text('#error stop\n')
            source.write_text('#include "error.h"\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertTrue(result.stderr.startswith(str(header) + ':1:'), result.stderr)

    def test_default_include_paths(self):
        paths = ['/custom']
        add_default_include_paths('/tmp/compiler/main.py', paths)
        self.assertEqual(paths, ['/custom', '/tmp/compiler/include', '/usr/local/include',
                                 '/usr/include/x86_64-linux-gnu', '/usr/include'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / 'compiler.pyz'
            headers = root / 'include'
            headers.mkdir()
            (headers / 'answer.h').write_text('int main(void){return 42;}\n')
            built = subprocess.run([sys.executable, str(Path(__file__).with_name('build.py')), '-o', str(archive)],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stderr)
            result = subprocess.run([sys.executable, str(archive), '-E', '-'],
                                    input='#include <answer.h>\n', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_program_returns(result.stdout, 42)
        if Path('/usr/include/linux/limits.h').exists():
            result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                    input='#include <linux/limits.h>\nint main(void){return PATH_MAX/128;}\n',
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_program_returns(result.stdout, 32)

    def test_include_directory_option(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, second = root / 'first', root / 'second'
            first.mkdir()
            second.mkdir()
            (root / 'answer.h').write_text('#define VALUE 42\n')
            (first / 'answer.h').write_text('#define VALUE 7\n')
            (second / 'answer.h').write_text('#define VALUE 11\n')
            source = root / 'main.c'
            for include, paths, expected in (
                    ('"answer.h"', [first, second], 42),
                    ('<answer.h>', [first, second], 7),
                    ('<answer.h>', [second, first], 11)):
                source.write_text('#include ' + include + '\nint main(void){return VALUE;}\n')
                result = subprocess.run([sys.executable, str(COMPILER), '-###', '-E',
                                         *['-I' + str(path) for path in paths], str(source)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('-I' + str(paths[0]), result.stderr)
                self.assert_program_returns(result.stdout, expected)
            result = subprocess.run([sys.executable, str(COMPILER), '-E', str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('cannot open', result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), '-I'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('chibicc (Python)', result.stderr)

    def test_angle_and_macro_includes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'main.c'
            header = Path(directory) / 'answer.h'
            header.write_text('#define VALUE 42\n')
            for directive in ('#include <answer.h>\n',
                              '#define HEADER "answer.h"\n#include HEADER\n',
                              '#define HEADER < answer.h\n#include HEADER >\n'):
                source.write_text(directive + 'int main(void){return VALUE;}\n')
                result = subprocess.run([sys.executable, str(COMPILER), '-E', '-I' + directory, str(source)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assert_program_returns(result.stdout, 42)
            literal_name = 'raw\\file.h'
            (Path(directory) / literal_name).write_text('int main(void){return 7;}\n')
            source.write_text('#include "' + literal_name + '"\n')
            result = subprocess.run([sys.executable, str(COMPILER), '-E', str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_program_returns(result.stdout, 7)
            subdir = Path(directory) / 'sub'
            subdir.mkdir()
            source = subdir / 'main.c'
            source.write_text('#include <answer.h>\nint main(void){return VALUE;}\n')
            result = subprocess.run([sys.executable, str(COMPILER.resolve()), '-E', str(source)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assert_program_returns(result.stdout, 42)
        result = compile_program('#include <missing.h\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected '>'", result.stderr)

    def test_line_continuation(self):
        self.assertEqual(remove_backslash_newline('a\\\nb\\\nc\nd\n'), 'abc\n\n\nd\n')
        self.assertEqual(remove_backslash_newline('a\\\nb'), 'ab\n')
        self.assert_program_returns('int main(void){return size\\\nof(char);}\n', 1)
        self.assert_program_returns('#define VALUE 7+\\\n35\nint main(void){return VALUE;}\n', 42)
        self.assert_program_returns('int main(void){return sizeof("ab\\\ncd");}\n', 5)
        self.assert_program_returns('// comment\\\ninvalid code\nint main(void){return 42;}\n', 42)
        result = compile_program('#define VALUE \\\n42\n\nint main(void){return missing;}\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('-:4: int main(void){return missing;}', result.stderr)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.c'
            path.write_text('int val\\\nue;\nint answer;\n')
            files = []
            tokens = tokenize_file(path, files)
            self.assertEqual(tokens[1].text, 'value')
            self.assertEqual(tokens[4].line_no, 3)
            self.assertEqual(files[0].contents.count('\n'), 3)

    def test_macro_expansion_spacing(self):
        prefix = '#define STR(x) #x\n#define FORWARD(x) STR(x)\n'
        for definition, expected in (
                ('#define WRAP(x) FORWARD(foo.x)\nWRAP(bar)\n', b'foo.bar\0'),
                ('#define WRAP(x) FORWARD(foo. x)\nWRAP(bar)\n', b'foo. bar\0'),
                ('#define NAME foo\n#define WRAP(x) FORWARD(x.NAME)\nWRAP(bar)\n', b'bar.foo\0'),
                ('#define NAME foo\n#define WRAP(x) FORWARD(x. NAME)\nWRAP(bar)\n', b'bar. foo\0')):
            self.assertEqual(tokenize(prefix + definition)[0].str, expected)
        for source, expected in (
                ('#define VALUE 42\nVALUE\nVALUE\n', '42\n42\n'),
                ('#define VALUE() 42\nVALUE()\nVALUE()\n', '42\n42\n'),
                ('#define EMPTY\n a EMPTY+b\n', 'a +b\n')):
            result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                    input=source, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)
        self.assert_program_returns('#define VALUE 42\nint main(void){return VALUE;}\n', 42)

    def test_undefined_names_in_conditions(self):
        for expression in ('UNKNOWN==0', '!UNKNOWN', 'UNKNOWN+2==2', 'KNOWN&&!UNKNOWN'):
            self.assert_program_returns('#define KNOWN 1\n#if ' + expression +
                                        '\nint main(void){return 42;}\n#else\ninvalid\n#endif\n', 42)
        self.assert_program_returns('#if UNKNOWN\ninvalid\n#elif ALSO_UNKNOWN\ninvalid\n#else\nint main(void){return 7;}\n#endif\n', 7)
        self.assert_program_returns('#define SELF SELF\n#if SELF==0\nint main(void){return 11;}\n#endif\n', 11)
        result = compile_program('int main(void){return UNKNOWN;}')
        self.assertEqual(result.returncode, 1)
        self.assertIn('undefined variable', result.stderr)

    def test_defined_operator(self):
        for expression in ('defined VALUE', 'defined(VALUE)', 'defined(VALUE)&&!defined(UNKNOWN)',
                           'defined(FUNCTION)', 'defined(VALUE)+defined(UNKNOWN)==1'):
            self.assert_program_returns('#define VALUE UNKNOWN\n#define FUNCTION() 7\n#if ' + expression +
                                        '\nint main(void){return 42;}\n#else\ninvalid\n#endif\n', 42)
        self.assert_program_returns('#define VALUE 7\n#undef VALUE\n#if defined(VALUE)\ninvalid\n#else\nint main(void){return 11;}\n#endif\n', 11)
        for expression, message in (('defined()', 'macro name must be an identifier'),
                                    ('defined 123', 'macro name must be an identifier'),
                                    ('defined(VALUE', "expected ')'")):
            result = compile_program('#if ' + expression + '\n#endif\n')
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_macro_token_pasting(self):
        for source, expected in (
                ('#define P(x,y) x##y\nint main(void){return P(1,5);}\n', 15),
                ('#define P(x,y) x##y\nint main(void){return P(0,xff);}\n', 255),
                ('#define P(x,y) x##y\nint main(void){int foobar=42;return P(foo,bar);}\n', 42),
                ('#define P(x,y) x##y\nint main(void){return P(5,)+P(,7);}\n', 12),
                ('#define i 5\n#define P(x,y) x##y\nint main(void){int i3=100;return P(1+i,3);}\n', 101),
                ('#define P(x) x##5\nint main(void){return P(1+2);}\n', 26),
                ('#define P(x) 2##x\nint main(void){return P(1+2);}\n', 23),
                ('#define P(x,y,z) x##y##z\nint main(void){return P(1,2,3);}\n', 123)):
            self.assert_program_returns(source, expected)
        for source, message in (
                ('#define P(x,y) x##y\nP(+,*)\n', 'an invalid token'),
                ('#define P() ##1\nP()\n', "'##' cannot appear at start"),
                ('#define P(x) x##\nP(1)\n', "'##' cannot appear at end")):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_macro_stringizing(self):
        tokens = tokenize('#define STR(x) #x\nSTR( a!b  ' + chr(96) + '""c )\n')
        self.assertEqual(tokens[0].kind, 'STR')
        self.assertEqual(tokens[0].str, b'a!b ' + bytes([96]) + b'""c\0')
        self.assertEqual(tokens[0].ty.size, 9)
        tokens = tokenize('#define VALUE 42\n#define STR(x) #x\nSTR(VALUE)\n')
        self.assertEqual(tokens[0].str, b'VALUE\0')
        tokens = tokenize('#define STR(x) #x\nSTR("a\\\\b")\n')
        self.assertEqual(tokens[0].str, b'"a\\\\b"\0')
        tokens = tokenize('#define STR(x) #x\nSTR()\n')
        self.assertEqual(tokens[0].str, b'\0')
        self.assert_program_returns('#define STR(x) #x\nint main(void){return STR(abc)[2];}\n', 99)
        result = compile_program('#define BAD(x) #other\nBAD(42)\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn("'#' is not followed by a macro parameter", result.stderr)

    def test_recursive_function_macros(self):
        self.assert_program_returns('int value(int x){return x;}\n#define value(x) value(x)+1\nint main(void){return value(41);}\n', 42)
        self.assert_program_returns('int dbl(int x){return x*x;}\n#define dbl(x) OTHER(x)*x\n#define OTHER(x) dbl(x)+3\nint main(void){return dbl(2);}\n', 10)
        self.assert_program_returns('int f(int x){return x*2;}\n#define f(x) f(x)+1\nint main(void){return f(f(1));}\n', 7)
        tokens = tokenize('#define G F\n#define F(x) G\nG(1)\n')
        self.assertEqual([t.text for t in tokens[:-1]], ['F'])
        self.assertEqual(tokens[0].hideset, frozenset({'F', 'G'}))
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                input='#define SELF() SELF()\nSELF()\n',
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SELF()', result.stdout)

    def test_parenthesized_macro_arguments(self):
        self.assert_program_returns('#define PRODUCT(x,y) x*y\nint main(void){return PRODUCT((2+3),4);}\n', 20)
        self.assert_program_returns('#define PRODUCT(x,y) x*y\nint main(void){return PRODUCT((2,3),4);}\n', 12)
        self.assert_program_returns('#define PRODUCT(x,y) x*y\nint sum(int x,int y){return x+y;}int main(void){return PRODUCT(sum(3,4),6);}\n', 42)
        self.assert_program_returns('#define ADD(x,y) (x)+(y)\nint main(void){return ADD(ADD(3,4),35);}\n', 42)
        result = compile_program('#define ID(x) x\nID((1\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('premature end of input', result.stderr)

    def test_empty_macro_arguments(self):
        self.assert_program_returns('#define JOIN(x,y) x y\nint main(void){return JOIN(,4+5);}\n', 9)
        self.assert_program_returns('#define JOIN(x,y) x y\nint main(void){return JOIN(42,);}\n', 42)
        self.assert_program_returns('#define IGNORE(x,y) 42\nint main(void){return IGNORE(,);}\n', 42)
        self.assert_program_returns('#define EMPTY\n#define JOIN(x,y) x y\nint main(void){return JOIN(EMPTY,7);}\n', 7)

    def test_parameterized_macros(self):
        self.assert_program_returns('#define PRODUCT(x,y) x*y\nint main(void){return PRODUCT(3+4,4+5);}\n', 24)
        self.assert_program_returns('#define PRODUCT(x,y) (x)*(y)\nint main(void){return PRODUCT(3+4,4+5);}\n', 63)
        self.assert_program_returns('#define VALUE 7\n#define SUM(x,y) x+y\nint main(void){return SUM(VALUE,35);}\n', 42)
        self.assert_program_returns('#define IGNORE(x) 42\nint main(void){return IGNORE();}\n', 42)
        for source, message in (
                ('#define F(x,y) x+y\nint main(void){return F(1);}\n', "expected ','"),
                ('#define F(x) x\nint main(void){return F(1,2);}\n', "expected ')'"),
                ('#define F(1) 42\n', 'expected an identifier'),
                ('#define F(x) x\nF(1\n', 'premature end of input')):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn(message, result.stderr)

    def test_zero_argument_macros_and_spacing(self):
        self.assert_program_returns('#define ANSWER() 42\nint main(void){return ANSWER ();}\n', 42)
        self.assert_program_returns('#define ANSWER() 42\nint main(void){int ANSWER=5;return ANSWER+ANSWER();}\n', 47)
        self.assert_program_returns('#define CALL ()\nint answer(void){return 42;}int main(void){return answer CALL;}\n', 42)
        self.assert_program_returns('#define EMPTY()\nint main(void){EMPTY() return 7;}\n', 7)
        self.assert_program_returns('#define ANSWER/**/()\nint answer(void){return 11;}int main(void){return answer ANSWER;}\n', 11)
        for source in ('#define F() 42\nint main(void){return F(1);}\n',):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn("expected ')'", result.stderr)
        tokens = tokenize_raw('a/**/(b)\n c +d')
        self.assertEqual([t.has_space for t in tokens[:-1]], [False, True, False, False, True, True, False])
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                input='int  main(void){/*gap*/return\t42;}\n', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'int main(void){ return 42;}\n')

    def test_ifdef_ifndef_directives(self):
        for prefix in ('#define PRESENT\n#ifdef PRESENT\n', '#ifndef ABSENT\n',
                       '#define PRESENT\n#undef PRESENT\n#ifndef PRESENT\n'):
            self.assert_program_returns(prefix + 'int main(void){return 42;}\n#else\ninvalid\n#endif\n', 42)
        self.assert_program_returns('#ifdef ABSENT\n#ifdef ALSO_ABSENT\ninvalid\n#endif\n#ifndef THIRD\ninvalid\n#endif\n#else\nint main(void){return 7;}\n#endif\n', 7)
        # This original step treats a non-identifier as an undefined name.
        self.assert_program_returns('#ifdef 123\ninvalid\n#else\nint main(void){return 11;}\n#endif\n', 11)
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / 'guard.h'
            source = Path(directory) / 'main.c'
            header.write_text('#ifndef GUARD\n#define GUARD\nint answer=42;\n#endif\n')
            source.write_text('#include "guard.h"\n#include "guard.h"\nint main(void){return answer;}\n')
            result = subprocess.run([sys.executable, str(COMPILER), '-E', str(source)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('int answer'), 1)
            self.assert_program_returns(result.stdout, 42)

    def test_recursive_object_macros(self):
        self.assert_program_returns('int main(void){int VALUE=6;\n#define VALUE VALUE+3\nreturn VALUE;}\n', 9)
        self.assert_program_returns('int main(void){int FIRST=3;\n#define FIRST SECOND*5\n#define SECOND FIRST+2\nreturn FIRST;}\n', 13)
        tokens = tokenize('#define FIRST SECOND\n#define SECOND FIRST\nFIRST FIRST\n')
        self.assertEqual([t.text for t in tokens[:-1]], ['FIRST', 'FIRST'])
        for token in tokens[:-1]:
            self.assertEqual(token.hideset, frozenset({'FIRST', 'SECOND'}))
        result = subprocess.run([sys.executable, str(COMPILER), '-E', '-'],
                                input='#define SELF SELF\nSELF\n', capture_output=True,
                                text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'SELF\n')

    def test_macros_in_conditions(self):
        self.assert_program_returns('''#define VALUE NEXT
#define NEXT 5
#if VALUE-5
invalid
#elif VALUE*2==10
int main(void){return 42;}
#else
invalid
#endif
''', 42)
        self.assert_program_returns('#define EMPTY\n#if 1\nint main(void){return 7;}\n#elif EMPTY\ninvalid\n#endif\n', 7)
        result = compile_program('#define EMPTY\n#if EMPTY\n#endif\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('no expression', result.stderr)
        self.assert_program_returns('#if UNKNOWN\ninvalid\n#else\nint main(void){return 11;}\n#endif\n', 11)

    def test_undef_directives(self):
        self.assert_program_returns('#define VALUE 7\n#define VALUE 11\n#undef VALUE\nint main(void){int VALUE=42;return VALUE;}\n', 42)
        self.assert_program_returns('#undef UNKNOWN\n#define VALUE 7\n#undef VALUE\n#define VALUE 11\nint main(void){return VALUE;}\n', 11)
        self.assert_program_returns('#define VALUE 7\n#if 0\n#undef VALUE\n#endif\nint main(void){return VALUE;}\n', 7)
        self.assert_program_returns('#define if 7\n#undef if\nint main(void){if (1) return 42;return 0;}\n', 42)
        result = compile_program('#undef 123\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('macro name must be an identifier', result.stderr)

    def test_object_like_macros(self):
        self.assert_program_returns('#define VALUE 3+4\nint main(void){return VALUE*5;}\n', 23)
        self.assert_program_returns('#define VALUE 3\n#define VALUE 42\nint main(void){return VALUE;}\n', 42)
        self.assert_program_returns('#define EMPTY\n#define FIRST SECOND\n#define SECOND 7\nint main(void){EMPTY return FIRST;}\n', 7)
        self.assert_program_returns('#define if 42\nint main(void){return if;}\n', 42)
        self.assert_program_returns('#define NAME 42\nint main(void){return sizeof("NAME");}\n', 5)
        self.assert_program_returns('#if 0\n#define VALUE 7\n#endif\nint main(void){int VALUE=11;return VALUE;}\n', 11)
        result = compile_program('#define 123 42\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('macro name must be an identifier', result.stderr)
        self.assertEqual([t.text for t in tokenize('#define VALUE 3\nVALUE\n')[:-1]], ['3'])
        self.assertEqual(tokenize('VALUE\n')[0].text, 'VALUE')

    def test_elif_directives(self):
        self.assert_program_returns('''#if 0
invalid
#elif 0
invalid
#elif 2+3
int main(void){return 42;}
#elif unknown_expression
invalid
#else
invalid
#endif
''', 42)
        self.assert_program_returns('#if 1\nint main(void){return 7;}\n#elif\ninvalid\n#endif\n', 7)
        self.assert_program_returns('#if 0\n#elif 0\n#else\nint main(void){return 11;}\n#endif\n', 11)
        for source in ('#elif 1\n', '#if 0\n#else\n#elif 1\n#endif\n'):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn('stray #elif', result.stderr)

    def test_else_directives(self):
        self.assert_program_returns('#if 0\ninvalid C\n#else\nint main(void){return 42;}\n#endif\n', 42)
        self.assert_program_returns('#if 1\nint main(void){return 7;}\n#else\n#include "/missing"\n#endif\n', 7)
        self.assert_program_returns('''#if 0
#if missing
#else
invalid
#endif
#else
#if 0
invalid
#else
int main(void){return 11;}
#endif
#endif
''', 11)
        for source in ('#else\n', '#if 0\n#else\n#else\n#endif\n'):
            result = compile_program(source)
            self.assertEqual(result.returncode, 1)
            self.assertIn('stray #else', result.stderr)

    def test_skip_nested_if(self):
        self.assert_program_returns('''#if 0
#if unknown_expression
#include "/does/not/exist"
#if also_unknown
invalid C
#endif
#endif
#endif
int main(void){return 42;}
''', 42)
        result = compile_program('#if 0\n#if missing_end\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('unterminated conditional directive', result.stderr)

    def test_if_endif_directives(self):
        source = '#if 0\n#include "/no/such/file"\ninvalid code\n#endif\n#if 2*3==6\nint main(void){return 42;}\n#endif\n'
        self.assert_program_returns(source, 42)
        self.assert_program_returns('#if 1\n#if 1\nint main(void){return 7;}\n#endif\n#endif\n', 7)
        for source, message in (
                ('#endif\n', 'stray #endif'),
                ('#if 1\n', 'unterminated conditional directive'),
                ('#if\n#endif\n', 'no expression'),
                ('#if 1 2\n#endif\n', 'extra token')):
            with self.subTest(source=source):
                result = compile_program(source)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_preprocess_only_option(self):
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / "answer.h"
            source = Path(directory) / "main.c"
            output = Path(directory) / "preprocessed.c"
            header.write_text("int value=42;\n")
            source.write_text('#include "answer.h"\nint main(void){return value;}\n')
            result = subprocess.run([sys.executable, str(COMPILER), "-E", str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "int value=42;\nint main(void){return value;}\n")
            self.assert_program_returns(result.stdout, 42)
            result = subprocess.run([sys.executable, str(COMPILER), "-E", "-o", str(output), "-"],
                                    input=f'#include "{header}"\n', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual(output.read_text(), "int value=42;\n")
            result = subprocess.run([sys.executable, str(COMPILER), "-E", "-o", str(output), str(source), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("multiple files", result.stderr)
        for text, expected in (("not_valid_c", "not_valid_c\n"), ("", "\n"), ("0x2a", "0x2a\n")):
            result = subprocess.run([sys.executable, str(COMPILER), "-E", "-"],
                                    input=text, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, expected)

    def test_extra_include_token_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            header = Path(directory) / "answer.h"
            source = Path(directory) / "main.c"
            header.write_text("int answer(void){return 42;}\n")
            source.write_text('#include "answer.h" int extra;\nint main(void){return answer();}\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("^ extra token\n", result.stderr)
            self.assertTrue(result.stderr.startswith(f"{source}:1:"), result.stderr)
            self.assertIn("  .globl extra\n", result.stdout)
            assembly = Path(directory) / "program.s"
            assembly.write_text(result.stdout)
            executable = Path(directory) / "program"
            subprocess.run(["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), str(assembly)], check=True)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            source.write_text('#include "answer.h" junk\nint main(void){return answer();}\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("extra token", result.stderr)
            source.write_text('#include "answer.h"\nint main(void){return answer();}\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")

    def test_quoted_include_files(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "main.c"
            headers = Path(directory) / "headers"
            (headers / "nested").mkdir(parents=True)
            first = headers / "first.h"
            second = headers / "nested" / "second.h"
            source.write_text('#include "headers/first.h"\nint main(void){return first();}\n')
            first.write_text('#include "nested/second.h"\nint first(void){return 20+second();}\n')
            second.write_text('int second(void){return 22;}\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for number, file in enumerate((source, first, second), 1):
                self.assertIn(f'  .file {number} "{file}"\n', result.stdout)
                self.assertIn(f"  .loc {number} ", result.stdout)
            assembly = Path(directory) / "program.s"
            assembly.write_text(result.stdout)
            executable = Path(directory) / "program"
            subprocess.run(["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), str(assembly)], check=True)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            files = []
            tokens = preprocess(tokenize_file(source, files), files)
            self.assertEqual([file.file_no for file in files], [1, 2, 3])
            self.assertTrue(any(token.text == "second" and token.file.file_no == 3 for token in tokens))
            for text, message in (("int bad(void){return missing;}\n", "undefined variable"),
                                  ('char *bad="\\x";\n', "invalid hex escape")):
                second.write_text(text)
                result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr.startswith(f"{second}:1:"), result.stderr)
                self.assertIn(message, result.stderr)
            source.write_text('#include "missing.h"\n')
            result = subprocess.run(compiler_command(str(source)), capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("missing.h", result.stderr)
            self.assertTrue(result.stderr.startswith(f"{source}:1:"), result.stderr)
        self.assertIn("cannot open", compile_program("#include <file.h>\n").stderr)

    def test_null_preprocessor_directives(self):
        self.assert_program_returns("#\n /* comment */ #\nint main(void){return 42;}\n#\n", 42)
        tokens = tokenize_raw(" /*comment*/ #\n int x; #\n")
        self.assertEqual([token.at_bol for token in tokens], [True, True, False, False, False, True])
        processed = preprocess(tokens)
        self.assertEqual([token.text for token in processed], ["int", "x", ";", "#", ""])
        self.assertFalse(processed[3].at_bol)
        self.assertFalse(tokenize_raw("int x; /*\n*/ #\n")[3].at_bol)
        result = compile_program("# junk\nint main(void){return 0;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("invalid preprocessor directive", result.stderr)
        self.assertIn("  mov $42, %rax\n", compile_program("#\nint main(void){return 42;}").stdout)

    def test_initial_preprocessing_stage(self):
        tokens = tokenize_raw("int ifx=42;return ifx;")
        self.assertEqual([token.kind for token in tokens[:2]], ["IDENT", "IDENT"])
        original_ids = [id(token) for token in tokens]
        result = preprocess(tokens)
        self.assertIs(result, tokens)
        self.assertEqual([id(token) for token in result], original_ids)
        self.assertEqual([token.kind for token in result[:2]], ["KEYWORD", "IDENT"])
        self.assertEqual(result[5].kind, "KEYWORD")
        self.assertEqual(result[3].value, 42)
        self.assert_program_returns("int main(void){return 42;}", 42)
        self.assertIn("  mov $42, %rax\n", compile_program("int main(void){return 42;}").stdout)

    def test_linker_driver_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "main.c"
            second = Path(directory) / "answer.c"
            first.write_text("int f(void);int main(void){return f();}\n")
            second.write_text("int f(void){return 42;}\n")
            executable = Path(directory) / "program"
            result = subprocess.run([sys.executable, str(COMPILER), "-###", "-o", str(executable), str(first), str(second)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(executable.read_bytes()[16:18], b"\x02\x00")
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            self.assertIn("ld -o ", result.stderr)
            self.assertIn("crtbegin.o", result.stderr)
            result = subprocess.run([sys.executable, str(COMPILER), "-c", str(first), str(second)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run([sys.executable, str(COMPILER), "main.o", "answer.o"], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(subprocess.run([str(Path(directory) / "a.out")], timeout=5).returncode, 42)
            result = subprocess.run([sys.executable, str(COMPILER), "-o", str(executable), "-"],
                                    input="int puts(char*);int main(void){puts(\"linked\");return 42;}", capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5)
            self.assertEqual((executed.returncode, executed.stdout), (42, "linked\n"))
            result = subprocess.run([sys.executable, str(COMPILER), "source.xyz"], cwd=directory,
                                    capture_output=True, text=True)
            self.assertIn("unknown file extension", result.stderr)

    def test_multiple_driver_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "main.c"
            second = Path(directory) / "answer.c"
            first.write_text("int f(void);int main(void){return f();}\n")
            second.write_text("int f(void){return 42;}\n")
            result = subprocess.run([sys.executable, str(COMPILER), "-c", str(first), str(second)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            objects = [str(Path(directory) / name) for name in ("main.o", "answer.o")]
            self.assertTrue(all(Path(name).read_bytes().startswith(b"\x7fELF") for name in objects))
            executable = Path(directory) / "program"
            subprocess.run(["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), *objects], check=True)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            result = subprocess.run([sys.executable, str(COMPILER), "-S", str(first), str(second)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f'  .file 1 "{first}"', (Path(directory) / "main.s").read_text())
            self.assertIn(f'  .file 1 "{second}"', (Path(directory) / "answer.s").read_text())
            result = subprocess.run([sys.executable, str(COMPILER), "-c", "-o", str(executable), str(first), str(second)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn("cannot specify '-o' with '-c,' '-S' or '-E' with multiple files", result.stderr)
        result = subprocess.run([sys.executable, str(COMPILER), "--help", "-o"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)

    def test_assembler_driver_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "program.c"
            source.write_text("int main(void){return 42;}\n")
            result = subprocess.run([sys.executable, str(COMPILER), "-c", str(source)], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            obj = Path(directory) / "program.o"
            self.assertEqual(obj.read_bytes()[:4], b"\x7fELF")
            self.assertEqual(obj.read_bytes()[16:18], b"\x01\x00")
            executable = Path(directory) / "program"
            subprocess.run(["gcc", "-static", "-Wl,-z,noexecstack", "-o", str(executable), str(obj)], check=True)
            self.assertEqual(subprocess.run([str(executable)], timeout=5).returncode, 42)
            result = subprocess.run([sys.executable, str(COMPILER), "-S", str(source)], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("  mov $42, %rax\n", (Path(directory) / "program.s").read_text())
            result = subprocess.run([sys.executable, str(COMPILER), "-c", "-###", "-o", str(obj), str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("as -c ", result.stderr)
            temporary = result.stderr.splitlines()[0].rsplit(" -cc1-output ", 1)[1]
            self.assertFalse(Path(temporary).exists())
            result = subprocess.run([sys.executable, str(COMPILER), "-c", "-o", directory, str(source)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            result = subprocess.run([sys.executable, str(COMPILER), "-c", "-o", "", str(source)],
                                    cwd=directory, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)

    def test_driver_and_cc1_split(self):
        source = "int main(void){return 42;}"
        direct = subprocess.run(compiler_command("-cc1", "-cc1-input", "-", "-"),
                                input=source, capture_output=True, text=True)
        driver = compile_program(source)
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(driver.returncode, 0, driver.stderr)
        self.assertEqual(driver.stdout, direct.stdout)
        traced = subprocess.run(compiler_command("-###", "-"),
                                input=source, capture_output=True, text=True)
        self.assertEqual(traced.returncode, 0, traced.stderr)
        self.assertEqual(traced.stdout, direct.stdout)
        self.assertIn("-cc1", traced.stderr)
        self.assertIn(str(COMPILER), traced.stderr)
        invalid = compile_program("int main(void){return missing;}")
        self.assertEqual(invalid.returncode, 1)
        self.assertEqual(invalid.stdout, "")
        self.assertEqual(invalid.stderr.count("undefined variable"), 1)
        self.assert_program_returns(source, 42)

    def test_function_pointer_common_type(self):
        for source, expected in [
            ("int f(void){return 42;}int main(void){return (1?f:(void*)0)();}", 42),
            ("int f(void){return 42;}int g(void){return 1;}int main(void){return (0?g:f)();}", 42),
            ("int f(void){return 42;}int main(void){return f!=(void*)0;}", 1),
            ("int f(void){return 42;}int(*p)(void)=1?f:(void*)0;int main(void){return p();}", 42),
        ]:
            self.assert_program_returns(source, expected)
        main = next(fn for fn in parse(tokenize("int f(void);int main(void){return (1?f:(void*)0)();}")) if fn.name == "main")
        conditional = main.body.body[0].lhs.lhs.lhs
        self.assertEqual((conditional.kind, conditional.ty.kind, conditional.ty.base.kind),
                         ("COND", "PTR", "FUNC"))
        self.assertIn("  call *%r10\n", compile_program("int f(void);int main(void){return (1?f:(void*)0)();}").stdout)

    def test_function_parameter_decay(self):
        self.assert_program_returns("int f(int x){return x+1;}int apply(int fn(int),int x){return fn(x);}int main(void){return apply(f,41);}", 42)
        self.assert_program_returns("int f(void){return 42;}int apply(int fn(void)){return fn();}int main(void){return apply(f);}", 42)
        function = parse(tokenize("int apply(int fn(int));"))[0]
        parameter = function.ty.params[0]
        self.assertEqual((parameter.kind, parameter.base.kind, parameter.size, parameter.name.text),
                         ("PTR", "FUNC", 8, "fn"))
        self.assertIsNotNone(parameter.name_pos)
        function = parse(tokenize("typedef int F(void);int apply(F);"))[0]
        self.assertEqual(function.ty.params[0].kind, "PTR")
        result = compile_program("typedef int F(void);int apply(F){return 0;}")
        self.assertEqual(result.returncode, 1)
        self.assertIn("parameter name omitted", result.stderr)
        self.assertIn("  mov %rdi, -8(%rbp)\n", compile_program("int apply(int fn(void)){return fn();}").stdout)

    def test_function_pointer_calls(self):
        for source, expected in [
            ("int f(int x){return x+1;}int main(void){return (f)(41);}", 42),
            ("int f(int x){return x+1;}int main(void){return (&f)(41);}", 42),
            ("int f(int x){return x+1;}int main(void){int(*p)(int)=f;return (*p)(41);}", 42),
            ("int f(int x){return x+1;}int(*p)(int)=f;int main(void){return p(41);}", 42),
            ("int f(int x){return x+1;}int main(void){struct T{int(*p)(int);} t={f};return t.p(41);}", 42),
        ]:
            self.assert_program_returns(source, expected)
        self.assert_program_returns("int f(int);int main(void){int(*p)(int)=f;return p(41);}", 42,
                                    "int f(int x){return x+1;}")
        assembly = compile_program("int f(int);int main(void){return f(41);}").stdout
        self.assertIn("  mov f@GOTPCREL(%rip), %rax\n", assembly)
        self.assertIn("  call *%r10\n", assembly)
        self.assertIn("  lea f(%rip), %rax\n", compile_program("int f(int x){return x;}int main(void){return f(42);}").stdout)
        self.assertIn("  .quad f+0\n", compile_program("int f(int);int(*p)(int)=f;").stdout)
        self.assertIn("not a function", compile_program("int main(void){int x=1;return x();}").stderr)

    def test_compiler_archive(self):
        global COMPILER
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "compiler.pyz"
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("build.py")),
                                     "-o", str(archive)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(archive.is_file())
            previous = COMPILER
            COMPILER = archive
            try:
                self.assert_program_returns("int main(void){return 42;}", 42)
                self.assertIn("  mov $42, %rax\n", compile_program("int main(void){return 42;}").stdout)
                self.assertEqual(compile_program("int main(void){return 42+;}").returncode, 1)
                help_result = subprocess.run([sys.executable, str(archive), "--help"],
                                             capture_output=True, text=True)
                self.assertEqual(help_result.returncode, 0)
            finally:
                COMPILER = previous

    def test_long_double_alias(self):
        self.assert_program_returns("long double g=20.5L;long double f(long double x){return x+g;}int main(void){return sizeof(long double)+f(13.5);}", 42)
        self.assert_program_returns("int main(void){double long x=42.0;return x;}", 42)
        variable = parse(tokenize("long double x;"))[0]
        self.assertEqual((variable.ty.kind, variable.ty.size, variable.ty.align), ("DOUBLE", 8, 8))
        self.assertEqual(compile_program("long long double x;").returncode, 1)

    def test_floating_constant_initializers(self):
        for source, expected in [
            ("float g=21.5*2-1;int main(void){return g;}", 42),
            ("double g=0.0?55:(0,1+1*5.0/2*(double)2*(int)2.0);int main(void){return g;}", 11),
            ("double a[]={-1.5,42.0};int main(void){return a[1];}", 42),
            ("struct T{float a;double b;} g={1.5,42};int main(void){return g.b;}", 42),
            ("int g=42.9;int main(void){return g;}", 42),
            ("double g=1.0/0.0;int main(void){return g>0;}", 1),
            ("float g=0.0/0.0;int main(void){return g!=g;}", 1),
        ]:
            self.assert_program_returns(source, expected)
        self.assertEqual(parse(tokenize("float g=42.0;"))[0].init_data, bytes.fromhex("00002842"))
        self.assertEqual(parse(tokenize("double g=42.0;"))[0].init_data, bytes.fromhex("0000000000004540"))
        self.assertIn("not a compile-time constant", compile_program("double f(void);double g=f();").stderr)
        self.assertIn("non-finite", compile_program("int g=1.0/0.0;").stderr)

    def test_variadic_floating_offsets(self):
        prefix = "typedef struct V{int gp_offset;int fp_offset;void *overflow;void *registers;} V;"
        function = "int f(double d,int n,...){V *v=(V*)__va_area__;char *p=v->registers;return *(int*)(p+v->gp_offset)+*(double*)(p+v->fp_offset);}"
        self.assert_program_returns(prefix + function + "int main(void){return f(7.0,1,20,22.0f);}", 42)
        self.assert_program_returns(prefix + function + "int call(void);int main(void){return call();}", 42,
                                    "int f(double,int,...);int call(void){return f(7.0,1,20,22.0);}")
        assembly = compile_program("int f(double x,int y,float z,...){return y;}").stdout
        self.assertIn("  movl $8,", assembly)
        self.assertIn("  movl $64,", assembly)
        self.assertIn("  movl $48,", compile_program("int f(int x,...){return x;}").stdout)

    def test_default_float_argument_promotion(self):
        self.assert_program_returns("int f();int main(void){float x=20.5f;return f(x,21.5f);}", 42,
                                    "int f(double a,double b){return a+b;}")
        for declaration, arguments, expected in [
            ("int f(int,...);", "0,1.5f", ["INT", "DOUBLE"]),
            ("int f();", "1.5f", ["DOUBLE"]),
            ("int f(float);", "1.5f", ["FLOAT"]),
        ]:
            main = next(fn for fn in parse(tokenize(declaration + f"int main(void){{return f({arguments});}}")) if fn.name == "main")
            call = main.body.body[0].lhs.lhs
            self.assertEqual([arg.ty.kind for arg in call.args], expected)
        self.assertIn("  cvtss2sd %xmm0, %xmm0\n", compile_program("int f();int main(void){return f(1.5f);}").stdout)

    def test_floating_parameter_definitions(self):
        for source, expected in [
            ("float f(float a,float b,float c){return a+b+c;}int main(void){return f(10.5,20.5,11);}", 42),
            ("double f(int a,double b,int c,float d){return a+b+c+d;}int main(void){return f(10,10.5,20,1.5);}", 42),
            ("double f(double a,double b,double c,double d,double e,double f,double g,double h){return a+b+c+d+e+f+g+h;}int main(void){return f(1,1,1,1,1,1,1,35);}", 42),
            ("double f(double x){if(x<=1)return 1;return x*f(x-1);}int main(void){return f(5);}", 120),
        ]:
            self.assert_program_returns(source, expected)
        self.assert_program_returns("int call(void);double f(int a,double b,float c){return a+b+c;}int main(void){return call();}", 42,
                                    "double f(int,double,float);int call(void){return f(20,20.5,1.5);}")
        assembly = compile_program("double f(float x,double y){return x+y;}").stdout
        self.assertIn("  movss %xmm0, -4(%rbp)\n", assembly)
        self.assertIn("  movsd %xmm1, -16(%rbp)\n", assembly)

    def test_floating_external_calls(self):
        helper = "float f(float a,float b){return a+b;}double d(double a,double b){return a+b;}double mix(int a,double b,int c,float d){return a+b+c+d;}"
        for source, expected in [
            ("float f(float,float);int main(void){return f(20.5,21.5);}", 42),
            ("double d(double,double);int main(void){return d(20.5,21.5);}", 42),
            ("double mix(int,double,int,float);int main(void){return mix(10,10.5,20,1.5);}", 42),
            ("double d(double,double);int main(void){return d(d(10.5,10),d(10.5,11));}", 42),
        ]:
            self.assert_program_returns(source, expected, helper)
        assembly = compile_program("double d(double,double);int main(void){return d(20.5,21.5);}").stdout
        self.assertIn("  movsd (%rsp), %xmm0\n", assembly)
        self.assertIn("  movsd (%rsp), %xmm1\n", assembly)
        self.assertIn("  call *%r10\n", assembly)
        self.assert_program_returns("int f(int,int);int main(void){int x=0;return f(++x,++x);}", 21, "int f(int a,int b){return 10*a+b;}")

    def test_floating_conditions(self):
        for source, expected in [
            ("int main(void){if(0.0)return 1;return 42;}", 42),
            ("int main(void){float x=0.5f;if(x)return 42;return 1;}", 42),
            ("int main(void){double x=3;int n=0;while(x){x--;n++;}return n;}", 3),
            ("int main(void){float x=3;int n=0;do n++;while(--x);return n;}", 3),
            ("int main(void){int x=0;0.0&&++x;0.5||++x;return x;}", 0),
            ("int main(void){return !0.0+!(-0.0f)+(0.5f&&2.0)+(0.0||2.0);}", 4),
            ("int main(void){return 0.0?1:42;}", 42),
            ("int main(void){return (_Bool)0.5f;}", 1),
            ("int main(void){return !(0.0/0.0);}", 1),
        ]:
            self.assert_program_returns(source, expected)
        for literal, clear, compare in (("0.0f", "xorps", "ucomiss"), ("0.0", "xorpd", "ucomisd")):
            assembly = compile_program(f"int main(void){{return !{literal};}}").stdout
            self.assertIn(f"  {clear} %xmm1, %xmm1\n  {compare} %xmm1, %xmm0\n", assembly)

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
        self.assertEqual(compile_program("int main(void){long double x;}").returncode, 0)

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
        self.assertIn("  call *%r10\n", compile_program("int f(int);int main(void){return f(42);}").stdout)

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
        function = next(obj for obj in parse(tokenize("int f(){return 42;}")) if obj.is_function and obj.is_definition)
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
        self.assertIn("  call *%r10\n", assembly)
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
            self.assertIn(f"  call *%r10\n  add $0, %rsp\n  {instruction}\n", assembly)

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
        self.assertIn("  mov %rax, %r10\n  mov $0, %rax\n  call *%r10\n  add $8, %rsp\n", assembly)
        assembly = compile_program("int alignment(void);int main(void){return alignment();}").stdout
        self.assertNotIn("  sub $8, %rsp\n", assembly)

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
        self.assertIn("  .data\n.L..2:\n  .byte 42\n", assembly)
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
        self.assertNotIn("  call *%r10\n", assembly)
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
        self.assertIn("  call *%r10\n", assembly)
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
        self.assertIn("  call *%r10\n", assembly)
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
            (r'int main(void){short a[2]=u"\xffff";return a[0]<0;}', 1),
        ]:
            self.assert_program_returns(source, expected)
        assembly = compile_program('int main(void){char a[4]="abc";return a[0];}').stdout
        self.assertIn("  mov $97, %rax\n", assembly)
        self.assertIn("  mov %al, (%rdi)\n", assembly)
        objects = parse(tokenize('int main(void){char x[]="abc";return x[0];}'))
        self.assertEqual([obj.init_data for obj in objects if not obj.is_function], [b'main\0', b'main\0'])

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
        self.assertNotIn("  call *%r10\n", assembly)
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
        function = next(obj for obj in parse(tokenize("int f(int x[][3]){return 0;}")) if obj.is_function and obj.is_definition)
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
        self.assertIn("  cmp $0, %eax\n  sete %al\n  movzx %al, %rax\n",
                      compile_program("int main(void){return !0;}").stdout)

    def test_integer_bases(self):
        for spelling, value in [("0777", 511), ("0xbeef", 48879), ("0XBEEF", 48879),
                                ("0b101111", 47), ("0B101111", 47), ("0", 0), ("42", 42)]:
            token = tokenize(spelling)[0]
            self.assertEqual((token.text, token.value), (spelling, value))
            self.assert_program_returns(f"int main(void){{return {spelling};}}", value & 255)
        for spelling in ("0b2", "0xG", "123abc", "0x"):
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
        function = next(obj for obj in parse(tokenize("enum {answer=42};int main(void){return answer;}")) if obj.is_function and obj.is_definition)
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
        call = next(obj for obj in parse(tokenize("int f(long x);int main(void){return f(-1);}")) if obj.is_function and obj.is_definition).body.body[0].lhs.lhs
        self.assertEqual(call.func_ty.kind, "FUNC")
        self.assertEqual((call.args[0].kind, call.args[0].ty.kind), ("CAST", "LONG"))
        assembly = compile_program("int f(long x);int main(void){return f(-1);}").stdout
        self.assertIn("  movsxd %eax, %rax\n", assembly)
        for kind in ("struct", "union"):
            result = compile_program(f"{kind} T{{int x;}};int f({kind} T x);int main(void){{{kind} T a;return f(a);}}")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_return_conversions(self):
        for source, expected in [
            ("char f(int x){return x;}int main(void){return f(261);}", 5),
            ("short f(void){return 65535;}int main(void){return f()<0;}", 1),
            ("long f(void){return -1;}int main(void){return f()<0;}", 1),
            ("int x;int *f(void){return &x;}int main(void){x=42;return *f();}", 42),
        ]:
            self.assert_program_returns(source, expected)
        node = next(obj for obj in parse(tokenize("char f(void){return 261;}")) if obj.is_function and obj.is_definition).body.body[0].lhs
        self.assertEqual((node.kind, node.ty.kind, node.lhs.kind), ("CAST", "CHAR", "NUM"))
        assembly = compile_program("char f(void){return 261;}").stdout
        self.assertIn("  movsbl %al, %eax\n  jmp .L.return.f", assembly)

    def test_declared_calls(self):
        self.assert_program_returns("int f();int main(void){return f();}int f(void){return 42;}", 42)
        call = next(obj for obj in parse(tokenize("char f();int main(void){return f();}")) if obj.is_function and obj.is_definition).body.body[0].lhs.lhs
        self.assertEqual(call.ty.kind, "CHAR")
        self.assert_program_returns("int f(int x){if(x==0)return 42;return f(x-1);}int main(void){return f(3);}", 42)
        for source, message in [
            ("int main(void){return missing();}", "implicit declaration of a function"),
            ("int main(void){int f;return f();}", "not a function"),
            ("typedef int f;int main(void){return f();}", "implicit declaration of a function"),
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
        self.assertEqual(compile_program("typedef int T;").stdout, '  .file 1 "-"\n')
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
        self.assertEqual([obj.is_definition for obj in program if obj.is_function], [True, False])
        prototype = next(obj for obj in program if obj.is_function and not obj.is_definition)
        self.assertIsNone(prototype.body)
        self.assertEqual(prototype.locals, [])
        assembly = compile_program("int f(int x);int f(int x){return x;}").stdout
        self.assertEqual(assembly.splitlines().count("f:"), 1)
        self.assertIn("  .byte 102\n  .byte 0\n", assembly)
        self.assertEqual(compile_program("int printf();").stdout, '  .file 1 "-"\n')
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
            ("int pair(int a,int b){return a+b;}int main(void){int x=0;return pair((x=1,7),x);}", 7),
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
        self.assertTrue(result.stdout.startswith('  .file 1 "-"\n'))
        locations = [line for line in result.stdout.splitlines() if ".loc " in line]
        self.assertEqual(locations, ["  .loc 1 2"] * 4)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source "quoted".c'
            assembly = Path(directory) / "program.s"
            executable = Path(directory) / "program"
            source.write_text(source_text)
            result = subprocess.run(compiler_command("-o", str(assembly), str(source)),
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
        result = compile_program("int main(void){\n ⟘\n}")
        self.assertIn("-:2:  ⟘\n", result.stderr)
        self.assertIn("^ invalid token", result.stderr)

    def test_upstream_c_programs(self):
        fixtures = Path(__file__).with_name("test")
        with tempfile.TemporaryDirectory() as directory:
            for source in sorted(fixtures.glob("*.c")):
                with self.subTest(source=source.name):
                    compiled = subprocess.run(compiler_command("-Iinclude", "-Itest", "test/" + source.name),
                                              cwd=fixtures.parent, capture_output=True, text=True)
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
        main = next(obj for obj in program if obj.name == "main")
        self.assertEqual([var.name for var in main.locals], ["y", "x", "x"])

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
                result = subprocess.run(compiler_command(*arguments),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(instruction_assembly(output.read_text()), expected)
            result = subprocess.run(compiler_command("-o", "-", str(source)),
                                    capture_output=True, text=True)
            self.assertEqual(instruction_assembly(result.stdout), expected)
            result = subprocess.run(compiler_command("-o" + str(output), "-"),
                                    input=source.read_text(), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(instruction_assembly(output.read_text()), expected)
            source.write_text("")
            result = subprocess.run(compiler_command("-o", str(output), str(source)),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(), f'  .file 1 "{source}"\n')
            source.write_text("int main(void){1=2;}")
            output.write_text("keep")
            result = subprocess.run(compiler_command("-o", str(output), str(source)),
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_text(), "keep")
            result = subprocess.run(compiler_command("-o", directory, "-"),
                                    input="int main(void){return 0;}", capture_output=True, text=True)
            self.assertIn("cannot open output file", result.stderr)
        result = subprocess.run(compiler_command("--help"), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("chibicc", result.stderr)
        result = subprocess.run(compiler_command("-o"), capture_output=True, text=True)
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
                result = subprocess.run(compiler_command(str(path)),
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(instruction_assembly(result.stdout), instruction_assembly(expected.stdout))
            path.write_text("int main(void){\n return missing;\n}\n")
            result = subprocess.run(compiler_command(str(path)),
                                    capture_output=True, text=True)
            prefix = f"{path}:2: "
            self.assertEqual(result.stderr, prefix + " return missing;\n"
                             + " " * (len(prefix) + 8) + "^ undefined variable\n")
            path.write_bytes(b"\xff")
            result = subprocess.run(compiler_command(str(path)),
                                    capture_output=True, text=True)
            self.assertIn("cannot decode", result.stderr)
        result = subprocess.run(compiler_command("/tmp/chibicc-no-such-source-40.c"),
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
        self.assertIn("  lea .L..2(%rip), %rax", assembly)
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
        functions = [obj for obj in objects if obj.is_function]
        self.assertEqual([obj.name for obj in functions], ["main", "a"])
        self.assertTrue(all(not obj.is_local for obj in functions))
        self.assertTrue(functions[1].locals[0].is_local)
        self.assertEqual(functions[1].ty.kind, "FUNC")
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
        function = next(obj for obj in parse(tokenize("int main(void){int x[2][3]; return x+1;}")) if obj.is_function and obj.is_definition)
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
        function = next(obj for obj in parse(tokenize("int main(void){int x[3]; return x;}")) if obj.is_function and obj.is_definition)
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
        function = next(obj for obj in parse(tokenize("int f(int x,int y){int z; return x-y;}")) if obj.is_function and obj.is_definition)
        self.assertEqual([var.name for var in function.params], ["x", "y"])
        self.assertEqual([var.name for var in function.locals], ["z", "x", "y"])
        assembly = CodeGenerator().generate([function])
        self.assertIn("  mov %edi, -8(%rbp)\n  mov %esi, -12(%rbp)\n", assembly)
        self.assertEqual(compile_program("int f(int a,int b,int c,int d,int e,int f,int g){} ").returncode, 0)
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
        self.assertIn("  pop %rdi\n  pop %rsi\n  pop %rdx\n  pop %rcx\n"
                      "  pop %r8\n  pop %r9\n", assembly)
        result = compile_program('int f();int main(void){return f(1,2,3,4,5,6,7);}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("  add $16, %rsp\n", result.stdout)
        for source in ['int f();int main(void){return f(1 2);}', 'int f();int main(void){return f(1,);}']:
            self.assertEqual(compile_program(source).returncode, 1)

    def test_zero_argument_calls(self):
        declarations = "int ret3();int ret5();"
        helpers = "int ret3(void) { return 3; } int ret5(void) { return 5; }"
        for source, expected in [('int main(void){return ret3();}', 3), ('int main(void){return ret5();}', 5),
                                 ('int main(void){return ret3()+ret5();}', 8)]:
            self.assert_program_returns(declarations + source, expected, helpers)
        call = next(obj for obj in parse(tokenize("int ret3();int main(void){return ret3();}")) if obj.is_function and obj.is_definition).body.body[0].lhs.lhs
        self.assertEqual(call.lhs.var.name, "ret3")
        self.assertEqual(call.ty.kind, "INT")
        assembly = compile_program(declarations + 'int main(void){return ret3();}').stdout
        self.assertIn("  call *%r10\n", assembly)
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
        program = next(obj for obj in parse(tokens) if obj.is_function and obj.is_definition)
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
                         ".L..3:\n  jmp .L.begin.1\n.L..2:\n" + EPILOGUE)
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
        program = next(obj for obj in parse(tokenize('int main(void){ ;;; return 5; }')) if obj.is_function and obj.is_definition)
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
        program = next(obj for obj in parse(tokenize('int main(void){ {1;} return 2; }')) if obj.is_function and obj.is_definition)
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
        self.assertEqual(compile_program("").stdout, '  .file 1 "-"\n')
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
            ("if(1) 2; else 3;", "  mov $1, %rax\n  cmp $0, %eax\n"
             "  je  .L.else.1\n  mov $2, %rax\n  jmp .L.end.1\n"
             ".L.else.1:\n  mov $3, %rax\n.L.end.1:\n"),
            ("if(0) ;", "  mov $0, %rax\n  cmp $0, %eax\n"
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
            ('int main(void){return 1;;}', 1),
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
            ('int main(void){int foo; foo=3; return foo;}', 3),
            ('int main(void){int foo123, bar; foo123=3; bar=5; return foo123+bar;}', 8),
            ('int main(void){int foo, foo123; foo=3; foo123=7; return foo+foo123;}', 10),
            ('int main(void){int Foo, foo; Foo=3; foo=7; return Foo+foo;}', 10),
            ('int main(void){int _, _value1; _=2; _value1=5; return _+_value1;}', 7),
            ('int main(void){int total, left, right; total=left=right=4; return total+left+right;}', 12),
            ('int main(void){int count; count=3; count=count+4; return count;}', 7),
            ('int main(void){int alpha, beta, gamma; alpha=1; beta=2; gamma=3; return alpha+beta+gamma;}', 6),
            ('int main(void){int a; a=3; return a;}', 3),
            ('int main(void){int a, z; a=3; z=5; return a+z;}', 8),
            ('int main(void){int a, b; a=b=3; return a+b;}', 6),
            ('int main(void){int a; a=1; a=a+2; return a;}', 3),
            ('int main(void){int a, b; a=4; b=7; a=9; return b;}', 7),
            ('int main(void){int a; a=5==5; return a;}', 1),
            ('int main(void){int a; a=3; return (a=7)+2;}', 9),
            ('int main(void){int a, b; a=-(3+4); b=2; return a/b;}', 253),
            ('int main(void){int a; (a)=6; return a;}', 6),
            ('int main(void){int a; a=65536*65536; return a/65536/65536;}', 0),
            ('int main(void){int a, z; a=2; z=8; (a+z)*(z-a); return a+z;}', 10),
            ('int main(void){1; 2; return 3;}', 3),
            ('int main(void){42; return 0;}', 0),
            ('int main(void){1+2; 3*(4+5); return (10-3)/2;}', 3),
            ('int main(void){5<6; return -7;}', 249),
            ('int main(void){10;\n return 20+22;\n}', 42),
            ('int main(void){return 0;}', 0),
            ('int main(void){return 42;}', 42),
            ('int main(void){return 5+20-4;}', 21),
            ('int main(void){ return 12 + 34 - 5 ;}', 41),
            ('int main(void){return 5+6*7;}', 47),
            ('int main(void){return 5*(9-6);}', 15),
            ('int main(void){return (3+5)/2;}', 4),
            ('int main(void){return 255;}', 255),
            ('int main(void){return 256;}', 0),
            ('int main(void){ return 0042 ;}', 34),
            ('int main(void){return 2147483647;}', 255),
            ('int main(void){return 10-3-2;}', 5),
            ('int main(void){return 0-1;}', 255),
            ('int main(void){return 255+2;}', 1),
            ('int main(void){return 5+ 20-4;}', 21),
            ('int main(void){return 5 +20-4;}', 21),
            ('int main(void){\treturn 12\n+\r34\x0b-\x0c5 ;}', 41),
            ('int main(void){return 1\u2003+\u20032;}', 3),
            ('int main(void){return 1+2147483647;}', 0),
            ('int main(void){return 0-2147483647-1;}', 0),
            ('int main(void){return (5+6)*7;}', 77),
            ('int main(void){return 20/3;}', 6),
            ('int main(void){return 20/2/2;}', 5),
            ('int main(void){return 20/(2/2);}', 20),
            ('int main(void){return 24/3*2;}', 16),
            ('int main(void){return 24/(3*2);}', 4),
            ('int main(void){return 20-3*4+8/2;}', 12),
            ('int main(void){return ((2+3)*(4+(8/2)));}', 40),
            ('int main(void){return ((42));}', 42),
            ('int main(void){return (0-7)/2;}', 253),
            ('int main(void){return 7/(0-2);}', 253),
            ('int main(void){return (0-7)/(0-2);}', 3),
            ('int main(void){return (0-3)*4;}', 244),
            ('int main(void){return 100/(2+3*(4-2));}', 12),
            ('int main(void){return 65536*65536/65536/65536;}', 0),
            ('int main(void){return -10+20;}', 10),
            ('int main(void){return - -10;}', 10),
            ('int main(void){return - - +10;}', 10),
            ('int main(void){return -1;}', 255),
            ('int main(void){return +42;}', 42),
            ('int main(void){return 1+-2;}', 255),
            ('int main(void){return 1- -2;}', 3),
            ('int main(void){return 1+ +2;}', 3),
            ('int main(void){return 1 + +2;}', 3),
            ('int main(void){return -(3+4)*2;}', 242),
            ('int main(void){return 2*-(3+4);}', 242),
            ('int main(void){return -20/3;}', 250),
            ('int main(void){return 20/-3;}', 250),
            ('int main(void){return -20/-3;}', 6),
            ('int main(void){return 3*-4+15;}', 3),
            ('int main(void){return -(-(-5));}', 251),
            ('int main(void){return -2147483647-1;}', 0),
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
            ('int main(void){return -1<0;}', 1),
            ('int main(void){return 0>-1;}', 1),
            ('int main(void){return -2<=-1;}', 1),
            ('int main(void){return -1>=0;}', 0),
            ('int main(void){return 2147483647+1>0;}', 0),
            ('int main(void){return 5+6*7==47;}', 1),
            ('int main(void){return 5+6*7!=47;}', 0),
            ('int main(void){return 5==2+3;}', 1),
            ('int main(void){return 3<4==1;}', 1),
            ('int main(void){return 3==4<5;}', 0),
            ('int main(void){return 1<2<3;}', 1),
            ('int main(void){return 3>2>0;}', 1),
            ('int main(void){return (3>2)+4;}', 5),
            ('int main(void){return (5>=5)*7;}', 7),
            ('int main(void){return 1==1==1;}', 1),
            ('int main(void){return 2==2==2;}', 0),
            ('int main(void){' + "".join(f"int var{i}={i};" for i in range(30))
             + "return " + "+".join(f"var{i}" for i in range(30)) + ";}", 179),
            ('int main(void){' + "".join(f"int {chr(97+i)}={i+1};" for i in range(26))
             + "return " + "+".join(chr(97+i) for i in range(26)) + ";}", 95),
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
            ("⟘=3;", "⟘=3;\n^ invalid token\n"),
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
                result = subprocess.run(compiler_command(*arguments),
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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--compiler", type=Path, default=COMPILER)
    options, arguments = parser.parse_known_args()
    COMPILER = options.compiler.resolve()
    unittest.main(argv=[sys.argv[0], *arguments], verbosity=2)
