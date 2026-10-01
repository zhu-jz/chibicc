"""Allocate local stack slots and generate x86-64 Linux assembly.

Based on chibicc commit 863e2b8de25fdf43a4a63b93d0f57718e9edaa47.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


import struct

from common import CompileError, align_to
from type import is_integer


ARGREG = ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9")
ARGREG8 = ("%dil", "%sil", "%dl", "%cl", "%r8b", "%r9b")
ARGREG16 = ("%di", "%si", "%dx", "%cx", "%r8w", "%r9w")
ARGREG32 = ("%edi", "%esi", "%edx", "%ecx", "%r8d", "%r9d")


I8 = "movsbl %al, %eax"
U8 = "movzbl %al, %eax"
I16 = "movswl %ax, %eax"
U16 = "movzwl %ax, %eax"
I64 = "movsxd %eax, %rax"
U64 = "mov %eax, %eax"
I32_F32 = "cvtsi2ssl %eax, %xmm0"
I32_F64 = "cvtsi2sdl %eax, %xmm0"
I64_F32 = "cvtsi2ssq %rax, %xmm0"
I64_F64 = "cvtsi2sdq %rax, %xmm0"
U32_F32 = "mov %eax, %eax; cvtsi2ssq %rax, %xmm0"
U32_F64 = "mov %eax, %eax; cvtsi2sdq %rax, %xmm0"
U64_F64 = ("test %rax,%rax; js 1f; pxor %xmm0,%xmm0; cvtsi2sd %rax,%xmm0; jmp 2f; "
           "1: mov %rax,%rdi; and $1,%eax; pxor %xmm0,%xmm0; shr %rdi; "
           "or %rax,%rdi; cvtsi2sd %rdi,%xmm0; addsd %xmm0,%xmm0; 2:")
F32_I32 = "cvttss2sil %xmm0, %eax"
F32_I64 = "cvttss2siq %xmm0, %rax"
F64_I32 = "cvttsd2sil %xmm0, %eax"
F64_I64 = "cvttsd2siq %xmm0, %rax"
# Columns and rows: signed 8/16/32/64, unsigned 8/16/32/64, float/double.
CAST_TABLE = (
    (None, None, None, I64, U8, U16, None, I64, I32_F32, I32_F64),
    (I8, None, None, I64, U8, U16, None, I64, I32_F32, I32_F64),
    (I8, I16, None, I64, U8, U16, None, I64, I32_F32, I32_F64),
    (I8, I16, None, None, U8, U16, None, None, I64_F32, I64_F64),
    (I8, None, None, I64, None, None, None, I64, I32_F32, I32_F64),
    (I8, I16, None, I64, U8, None, None, I64, I32_F32, I32_F64),
    (I8, I16, None, U64, U8, U16, None, U64, U32_F32, U32_F64),
    (I8, I16, None, None, U8, U16, None, None, I64_F32, U64_F64),
    (F32_I32+"; "+I8, F32_I32+"; "+I16, F32_I32, F32_I64,
     F32_I32+"; "+U8, F32_I32+"; "+U16, F32_I64, F32_I64, None, "cvtss2sd %xmm0, %xmm0"),
    (F64_I32+"; "+I8, F64_I32+"; "+I16, F64_I32, F64_I64,
     F64_I32+"; "+U8, F64_I32+"; "+U16, F64_I64, F64_I64, "cvtsd2ss %xmm0, %xmm0", None),
)


class CodeGenerator:
    def __init__(self):
        self.assembly = []
        self.depth = 0
        self.label_count = 0
        self.current_fn = None

    def push(self):
        self.assembly.append("  push %rax")
        self.depth += 1

    def pop(self, register):
        self.assembly.append(f"  pop {register}")
        self.depth -= 1

    def gen_addr(self, node):
        if node.kind == "VAR":
            if node.var.is_local:
                self.assembly.append(f"  lea {node.var.offset}(%rbp), %rax")
            else:
                self.assembly.append(f"  lea {node.var.name}(%rip), %rax")
            return
        if node.kind == "DEREF":
            self.gen_expr(node.lhs)
            return
        if node.kind == "COMMA":
            self.gen_expr(node.lhs)
            self.gen_addr(node.rhs)
            return
        if node.kind == "MEMBER":
            self.gen_addr(node.lhs)
            self.assembly.append(f"  add ${node.member.offset}, %rax")
            return
        raise CompileError(node.tok, "not an lvalue")

    def load(self, ty):
        if ty.kind in ("ARRAY", "STRUCT", "UNION"):
            return
        if ty.kind in ("FLOAT", "DOUBLE"):
            instruction = "movss" if ty.kind == "FLOAT" else "movsd"
            self.assembly.append(f"  {instruction} (%rax), %xmm0")
            return
        if ty.size == 1:
            instruction = "movzbl" if ty.is_unsigned else "movsbl"
            self.assembly.append(f"  {instruction} (%rax), %eax")
        elif ty.size == 2:
            instruction = "movzwl" if ty.is_unsigned else "movswl"
            self.assembly.append(f"  {instruction} (%rax), %eax")
        elif ty.size == 4:
            self.assembly.append("  movsxd (%rax), %rax")
        else:
            self.assembly.append("  mov (%rax), %rax")

    def store(self, ty):
        self.pop("%rdi")
        if ty.kind in ("FLOAT", "DOUBLE"):
            instruction = "movss" if ty.kind == "FLOAT" else "movsd"
            self.assembly.append(f"  {instruction} %xmm0, (%rdi)")
            return
        if ty.kind in ("STRUCT", "UNION"):
            for offset in range(ty.size):
                self.assembly.append(f"  mov {offset}(%rax), %r8b")
                self.assembly.append(f"  mov %r8b, {offset}(%rdi)")
            return
        if ty.size == 1:
            self.assembly.append("  mov %al, (%rdi)")
        elif ty.size == 2:
            self.assembly.append("  mov %ax, (%rdi)")
        elif ty.size == 4:
            self.assembly.append("  mov %eax, (%rdi)")
        else:
            self.assembly.append("  mov %rax, (%rdi)")

    def pushf(self):
        self.assembly.extend(("  sub $8, %rsp", "  movsd %xmm0, (%rsp)"))
        self.depth += 1

    def popf(self, index):
        self.assembly.extend((f"  movsd (%rsp), %xmm{index}", "  add $8, %rsp"))
        self.depth -= 1

    def cmp_zero(self, ty):
        if ty.kind in ("FLOAT", "DOUBLE"):
            suffix = "ss" if ty.kind == "FLOAT" else "sd"
            clear = "xorps" if ty.kind == "FLOAT" else "xorpd"
            self.assembly.extend((f"  {clear} %xmm1, %xmm1",
                                  f"  ucomi{suffix} %xmm1, %xmm0"))
            return
        register = "%eax" if is_integer(ty) and ty.size <= 4 else "%rax"
        self.assembly.append(f"  cmp $0, {register}")

    def cast(self, from_ty, to_ty):
        if to_ty.kind == "VOID":
            return
        if to_ty.kind == "BOOL":
            self.cmp_zero(from_ty)
            self.assembly.extend(("  setne %al", "  movzx %al, %eax"))
            return
        type_ids = {"CHAR": 0, "SHORT": 1, "INT": 2, "LONG": 3}
        source = type_ids[from_ty.kind] + (4 if from_ty.is_unsigned else 0) if from_ty.kind in type_ids else 7
        target = type_ids[to_ty.kind] + (4 if to_ty.is_unsigned else 0) if to_ty.kind in type_ids else 7
        if from_ty.kind in ("FLOAT", "DOUBLE"):
            source = 8 if from_ty.kind == "FLOAT" else 9
        if to_ty.kind in ("FLOAT", "DOUBLE"):
            target = 8 if to_ty.kind == "FLOAT" else 9
        instruction = CAST_TABLE[source][target]
        if instruction is not None:
            self.assembly.extend("  " + part for part in instruction.split("; "))

    def gen_expr(self, node):
        if node.tok is not None:
            self.assembly.append(f"  .loc 1 {node.tok.line_no}")
        if node.kind == "NULL_EXPR":
            return
        if node.kind == "MEMZERO":
            self.assembly.extend((f"  mov ${node.var.ty.size}, %rcx",
                                  f"  lea {node.var.offset}(%rbp), %rdi",
                                  "  mov $0, %al", "  rep stosb"))
            return
        if node.kind == "NUM":
            if node.ty.kind in ("FLOAT", "DOUBLE"):
                format_code = "f" if node.ty.kind == "FLOAT" else "d"
                try:
                    data = struct.pack("<" + format_code, node.fvalue)
                except OverflowError:
                    data = struct.pack("<" + format_code, float("inf"))
                bits = int.from_bytes(data, "little")
                register = "%eax" if node.ty.kind == "FLOAT" else "%rax"
                self.assembly.extend((f"  mov ${bits}, {register}  # {node.ty.kind.lower()} {node.fvalue:.6f}",
                                      "  movq %rax, %xmm0"))
                return
            self.assembly.append(f"  mov ${node.value}, %rax")
            return
        if node.kind == "NEG":
            self.gen_expr(node.lhs)
            if node.ty.kind in ("FLOAT", "DOUBLE"):
                bit = 31 if node.ty.kind == "FLOAT" else 63
                instruction = "xorps" if node.ty.kind == "FLOAT" else "xorpd"
                self.assembly.extend(("  mov $1, %rax", f"  shl ${bit}, %rax",
                                      "  movq %rax, %xmm1", f"  {instruction} %xmm1, %xmm0"))
                return
            self.assembly.append("  neg %rax")
            return
        if node.kind in ("VAR", "MEMBER"):
            self.gen_addr(node)
            self.load(node.ty)
            return
        if node.kind == "DEREF":
            self.gen_expr(node.lhs)
            self.load(node.ty)
            return
        if node.kind == "ADDR":
            self.gen_addr(node.lhs)
            return
        if node.kind == "ASSIGN":
            self.gen_addr(node.lhs)
            self.push()
            self.gen_expr(node.rhs)
            self.store(node.ty)
            return
        if node.kind == "FUNCALL":
            fp_count = sum(arg.ty.kind in ("FLOAT", "DOUBLE") for arg in node.args)
            if len(node.args) - fp_count > len(ARGREG):
                raise CompileError(node.tok, "at most 6 arguments are supported")
            if fp_count > 8:
                raise CompileError(node.tok, "at most 8 floating arguments are supported")
            for arg in reversed(node.args):
                self.gen_expr(arg)
                if arg.ty.kind in ("FLOAT", "DOUBLE"):
                    self.pushf()
                else:
                    self.push()
            gp, fp = 0, 0
            for arg in node.args:
                if arg.ty.kind in ("FLOAT", "DOUBLE"):
                    self.popf(fp)
                    fp += 1
                else:
                    self.pop(ARGREG[gp])
                    gp += 1
            if self.depth % 2:
                self.assembly.extend(("  sub $8, %rsp", f"  call {node.funcname}",
                                      "  add $8, %rsp"))
            else:
                self.assembly.append(f"  call {node.funcname}")
            if node.ty.kind == "BOOL":
                self.assembly.append("  movzx %al, %eax")
            elif node.ty.kind == "CHAR":
                instruction = "movzbl" if node.ty.is_unsigned else "movsbl"
                self.assembly.append(f"  {instruction} %al, %eax")
            elif node.ty.kind == "SHORT":
                instruction = "movzwl" if node.ty.is_unsigned else "movswl"
                self.assembly.append(f"  {instruction} %ax, %eax")
            return
        if node.kind == "STMT_EXPR":
            for statement in node.body:
                self.gen_stmt(statement)
            return
        if node.kind == "COMMA":
            self.gen_expr(node.lhs)
            self.gen_expr(node.rhs)
            return
        if node.kind == "CAST":
            self.gen_expr(node.lhs)
            self.cast(node.lhs.ty, node.ty)
            return
        if node.kind == "COND":
            self.label_count += 1
            label = self.label_count
            self.gen_expr(node.cond)
            self.cmp_zero(node.cond.ty)
            self.assembly.append(f"  je .L.else.{label}")
            self.gen_expr(node.then)
            self.assembly.extend((f"  jmp .L.end.{label}", f".L.else.{label}:"))
            self.gen_expr(node.els)
            self.assembly.append(f".L.end.{label}:")
            return
        if node.kind == "NOT":
            self.gen_expr(node.lhs)
            self.cmp_zero(node.lhs.ty)
            self.assembly.extend(("  sete %al", "  movzx %al, %rax"))
            return
        if node.kind == "BITNOT":
            self.gen_expr(node.lhs)
            self.assembly.append("  not %rax")
            return
        if node.kind in ("LOGAND", "LOGOR"):
            self.label_count += 1
            label = self.label_count
            is_and = node.kind == "LOGAND"
            branch = "je" if is_and else "jne"
            destination = f".L.false.{label}" if is_and else f".L.true.{label}"
            self.gen_expr(node.lhs)
            self.cmp_zero(node.lhs.ty)
            self.assembly.append(f"  {branch} {destination}")
            self.gen_expr(node.rhs)
            self.cmp_zero(node.rhs.ty)
            self.assembly.extend((f"  {branch} {destination}",
                                  f"  mov ${1 if is_and else 0}, %rax", f"  jmp .L.end.{label}",
                                  f"{destination}:", f"  mov ${0 if is_and else 1}, %rax",
                                  f".L.end.{label}:"))
            return

        # Save the right result, compute the left, then restore the right.
        if node.lhs.ty.kind in ("FLOAT", "DOUBLE"):
            self.gen_expr(node.rhs)
            self.pushf()
            self.gen_expr(node.lhs)
            self.popf(1)
            suffix = "ss" if node.lhs.ty.kind == "FLOAT" else "sd"
            if node.kind in ("+", "-", "*", "/"):
                instruction = {"+": "add", "-": "sub", "*": "mul", "/": "div"}[node.kind]
                self.assembly.append(f"  {instruction}{suffix} %xmm1, %xmm0")
                return
            if node.kind not in ("==", "!=", "<", "<="):
                raise CompileError(node.tok, "invalid expression")
            self.assembly.append(f"  ucomi{suffix} %xmm0, %xmm1")
            if node.kind == "==":
                self.assembly.extend(("  sete %al", "  setnp %dl", "  and %dl, %al"))
            elif node.kind == "!=":
                self.assembly.extend(("  setne %al", "  setp %dl", "  or %dl, %al"))
            else:
                self.assembly.append("  seta %al" if node.kind == "<" else "  setae %al")
            self.assembly.extend(("  and $1, %al", "  movzb %al, %rax"))
            return
        self.gen_expr(node.rhs)
        self.push()
        self.gen_expr(node.lhs)
        self.pop("%rdi")

        if node.lhs.ty.kind == "LONG" or node.lhs.ty.base is not None:
            ax, di = "%rax", "%rdi"
        else:
            ax, di = "%eax", "%edi"

        if node.kind == "+":
            self.assembly.append(f"  add {di}, {ax}")
        elif node.kind == "-":
            self.assembly.append(f"  sub {di}, {ax}")
        elif node.kind == "*":
            self.assembly.append(f"  imul {di}, {ax}")
        elif node.kind in ("&", "|", "^"):
            instruction = {"&": "and", "|": "or", "^": "xor"}[node.kind]
            self.assembly.append(f"  {instruction} {di}, {ax}")
        elif node.kind in ("<<", ">>"):
            self.assembly.append("  mov %rdi, %rcx")
            instruction = "shl" if node.kind == "<<" else "shr" if node.lhs.ty.is_unsigned else "sar"
            self.assembly.append(f"  {instruction} %cl, {ax}")
        elif node.kind in ("/", "%"):
            if node.ty.is_unsigned:
                dx = "%rdx" if ax == "%rax" else "%edx"
                self.assembly.extend((f"  mov $0, {dx}", f"  div {di}"))
            else:
                self.assembly.append("  cqo" if node.lhs.ty.size == 8 else "  cdq")
                self.assembly.append(f"  idiv {di}")
            if node.kind == "%":
                self.assembly.append("  mov %rdx, %rax")
        elif node.kind in ("==", "!=", "<", "<="):
            instructions = {
                "==": "sete", "!=": "setne", "<": "setl", "<=": "setle",
            }
            if node.lhs.ty.is_unsigned:
                instructions.update({"<": "setb", "<=": "setbe"})
            self.assembly.append(f"  cmp {di}, {ax}")
            self.assembly.append(f"  {instructions[node.kind]} %al")
            self.assembly.append("  movzb %al, %rax")
        else:
            raise CompileError(node.tok, "invalid expression")

    def gen_stmt(self, node):
        if node.tok is not None:
            self.assembly.append(f"  .loc 1 {node.tok.line_no}")
        if node.kind == "IF":
            self.label_count += 1
            label = self.label_count
            self.gen_expr(node.cond)
            self.cmp_zero(node.cond.ty)
            self.assembly.append(f"  je  .L.else.{label}")
            self.gen_stmt(node.then)
            self.assembly.append(f"  jmp .L.end.{label}")
            self.assembly.append(f".L.else.{label}:")
            if node.els is not None:
                self.gen_stmt(node.els)
            self.assembly.append(f".L.end.{label}:")
            return
        if node.kind == "FOR":
            self.label_count += 1
            label = self.label_count
            if node.init is not None:
                self.gen_stmt(node.init)
            self.assembly.append(f".L.begin.{label}:")
            if node.cond is not None:
                self.gen_expr(node.cond)
                self.cmp_zero(node.cond.ty)
                self.assembly.append(f"  je {node.brk_label}")
            self.gen_stmt(node.then)
            self.assembly.append(f"{node.cont_label}:")
            if node.inc is not None:
                self.gen_expr(node.inc)
            self.assembly.append(f"  jmp .L.begin.{label}")
            self.assembly.append(f"{node.brk_label}:")
            return
        if node.kind == "DO":
            self.label_count += 1
            label = self.label_count
            self.assembly.append(f".L.begin.{label}:")
            self.gen_stmt(node.then)
            self.assembly.append(f"{node.cont_label}:")
            self.gen_expr(node.cond)
            self.cmp_zero(node.cond.ty)
            self.assembly.extend((f"  jne .L.begin.{label}",
                                  f"{node.brk_label}:"))
            return
        if node.kind == "SWITCH":
            self.gen_expr(node.cond)
            register = "%rax" if node.cond.ty.size == 8 else "%eax"
            for case in node.cases:
                self.assembly.extend((f"  cmp ${case.value}, {register}", f"  je {case.label}"))
            if node.default_case is not None:
                self.assembly.append(f"  jmp {node.default_case.label}")
            self.assembly.append(f"  jmp {node.brk_label}")
            self.gen_stmt(node.then)
            self.assembly.append(f"{node.brk_label}:")
            return
        if node.kind == "CASE":
            self.assembly.append(f"{node.label}:")
            self.gen_stmt(node.lhs)
            return
        if node.kind == "BLOCK":
            for statement in node.body:
                self.gen_stmt(statement)
            return
        if node.kind == "RETURN":
            if node.lhs is not None:
                self.gen_expr(node.lhs)
            self.assembly.append(f"  jmp .L.return.{self.current_fn.name}")
            return
        if node.kind == "GOTO":
            self.assembly.append(f"  jmp {node.unique_label}")
            return
        if node.kind == "LABEL":
            self.assembly.append(f"{node.unique_label}:")
            self.gen_stmt(node.lhs)
            return
        if node.kind == "EXPR_STMT":
            self.gen_expr(node.lhs)
            return
        raise CompileError(node.tok, "invalid statement")

    def store_gp(self, index, var):
        if var.ty.size == 1:
            register = ARGREG8[index]
        elif var.ty.size == 2:
            register = ARGREG16[index]
        elif var.ty.size == 4:
            register = ARGREG32[index]
        elif var.ty.size == 8:
            register = ARGREG[index]
        else:
            raise CompileError(var.ty.name, "unsupported parameter size")
        self.assembly.append(f"  mov {register}, {var.offset}(%rbp)")

    def generate(self, program):
        self.assembly = []
        for var in program:
            if not var.is_function and var.is_definition:
                section = ".data" if var.init_data is not None else ".bss"
                visibility = ".local" if var.is_static else ".globl"
                self.assembly.extend([f"  {visibility} {var.name}", f"  .align {var.align}",
                                      f"  {section}", f"{var.name}:"])
                if var.init_data is not None:
                    relocations = {rel.offset: rel for rel in var.relocations}
                    position = 0
                    while position < var.ty.size:
                        if position in relocations:
                            rel = relocations[position]
                            self.assembly.append(f"  .quad {rel.label}{rel.addend:+d}")
                            position += 8
                        else:
                            self.assembly.append(f"  .byte {var.init_data[position]}")
                            position += 1
                else:
                    self.assembly.append(f"  .zero {var.ty.size}")
        for function in program:
            if not function.is_function or not function.is_definition:
                continue
            offset = 0
            for var in function.locals:
                offset += var.ty.size
                offset = align_to(offset, var.align)
                var.offset = -offset
            function.stack_size = align_to(offset, 16)
            self.current_fn = function
            directive = ".local" if function.is_static else ".globl"
            self.assembly.extend([f"  {directive} {function.name}", "  .text", f"{function.name}:",
                                  "  push %rbp", "  mov %rsp, %rbp",
                                  f"  sub ${function.stack_size}, %rsp"])
            if function.va_area is not None:
                offset = function.va_area.offset
                self.assembly.extend((f"  movl ${len(function.params) * 8}, {offset}(%rbp)",
                                      f"  movl $0, {offset + 4}(%rbp)",
                                      f"  movq %rbp, {offset + 16}(%rbp)",
                                      f"  addq ${offset + 24}, {offset + 16}(%rbp)"))
                for index, register in enumerate(ARGREG):
                    self.assembly.append(f"  movq {register}, {offset + 24 + index * 8}(%rbp)")
                for index in range(8):
                    self.assembly.append(f"  movsd %xmm{index}, {offset + 72 + index * 8}(%rbp)")
            if len(function.params) > len(ARGREG):
                raise CompileError(function.params[6].ty.name,
                                   "at most 6 parameters are supported")
            for index, var in enumerate(function.params):
                self.store_gp(index, var)
            self.gen_stmt(function.body)
            assert self.depth == 0
            self.assembly.extend([f".L.return.{function.name}:", "  mov %rbp, %rsp",
                                  "  pop %rbp", "  ret"])
        return "\n".join(self.assembly)


def codegen(program):
    return CodeGenerator().generate(program)
