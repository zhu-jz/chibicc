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
GP_MAX = 6
FP_MAX = 8


def reg_dx(size):
    return {1: "%dl", 2: "%dx", 4: "%edx", 8: "%rdx"}[size]


def reg_ax(size):
    return {1: "%al", 2: "%ax", 4: "%eax", 8: "%rax"}[size]


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

# Extend the existing conversions with the x87 80-bit floating register format.
FROM_F80 = ("fnstcw -10(%rsp); movzwl -10(%rsp), %eax; or $12, %ah; "
            "mov %ax, -12(%rsp); fldcw -12(%rsp); ")
RESTORE_F80 = " -24(%rsp); fldcw -10(%rsp); "
TO_F80 = (
    "mov %eax, -4(%rsp); fildl -4(%rsp)",
    "mov %eax, -4(%rsp); fildl -4(%rsp)",
    "mov %eax, -4(%rsp); fildl -4(%rsp)",
    "movq %rax, -8(%rsp); fildll -8(%rsp)",
    "mov %eax, -4(%rsp); fildl -4(%rsp)",
    "mov %eax, -4(%rsp); fildl -4(%rsp)",
    "mov %eax, %eax; mov %rax, -8(%rsp); fildll -8(%rsp)",
    "mov %rax, -8(%rsp); fildq -8(%rsp); test %rax, %rax; jns 1f; "
    "mov $1602224128, %eax; mov %eax, -4(%rsp); fadds -4(%rsp); 1:",
    "movss %xmm0, -4(%rsp); flds -4(%rsp)",
    "movsd %xmm0, -8(%rsp); fldl -8(%rsp)",
)
CAST_TABLE = tuple(row + (conversion,) for row, conversion in zip(CAST_TABLE, TO_F80)) + (
    (FROM_F80 + "fistps" + RESTORE_F80 + "movsbl -24(%rsp), %eax",
     FROM_F80 + "fistps" + RESTORE_F80 + "movzbl -24(%rsp), %eax",
     FROM_F80 + "fistpl" + RESTORE_F80 + "mov -24(%rsp), %eax",
     FROM_F80 + "fistpq" + RESTORE_F80 + "mov -24(%rsp), %rax",
     FROM_F80 + "fistps" + RESTORE_F80 + "movzbl -24(%rsp), %eax",
     FROM_F80 + "fistpl" + RESTORE_F80 + "movswl -24(%rsp), %eax",
     FROM_F80 + "fistpl" + RESTORE_F80 + "mov -24(%rsp), %eax",
     FROM_F80 + "fistpq" + RESTORE_F80 + "mov -24(%rsp), %rax",
     "fstps -8(%rsp); movss -8(%rsp), %xmm0",
     "fstpl -8(%rsp); movsd -8(%rsp), %xmm0", None),
)


def long_double_bytes(value):
    """Round an exact ratio to x86 extended precision, with six padding bytes."""
    numerator, denominator = value.as_integer_ratio()
    sign = int(numerator < 0)
    numerator = abs(numerator)
    if numerator == 0:
        return bytes(16)
    exponent = numerator.bit_length() - denominator.bit_length()
    if (numerator < denominator << exponent if exponent >= 0
            else numerator << -exponent < denominator):
        exponent -= 1
    shift = 63 - max(exponent, -16382)
    scaled_num = numerator << shift if shift >= 0 else numerator
    scaled_den = denominator if shift >= 0 else denominator << -shift
    significand, remainder = divmod(scaled_num, scaled_den)
    if remainder * 2 > scaled_den or (remainder * 2 == scaled_den and significand % 2):
        significand += 1
    if significand == 1 << 64:
        significand >>= 1
        exponent += 1
    biased = max(exponent + 16383, 1) if significand >= 1 << 63 else 0
    if exponent > 16383:
        biased, significand = 0x7fff, 1 << 63
    return significand.to_bytes(8, "little") + (biased | sign << 15).to_bytes(2, "little") + bytes(6)


def has_flonum(ty, lo, hi, offset=0):
    """Whether every member starting in this byte range is floating point."""
    if ty.kind in ("STRUCT", "UNION"):
        return all(has_flonum(member.ty, lo, hi, offset + member.offset)
                   for member in ty.members)
    if ty.kind == "ARRAY":
        return all(has_flonum(ty.base, lo, hi, offset + ty.base.size * i)
                   for i in range(ty.array_len))
    return offset < lo or hi <= offset or ty.kind in ("FLOAT", "DOUBLE")


class CodeGenerator:
    def __init__(self, fcommon=True, fpic=False):
        self.fcommon = fcommon
        self.fpic = fpic
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
            if node.var.ty.kind == "VLA":
                self.assembly.append(f"  mov {node.var.offset}(%rbp), %rax")
            elif node.var.is_local:
                self.assembly.append(f"  lea {node.var.offset}(%rbp), %rax")
            elif self.fpic:
                if node.var.is_tls:
                    self.assembly.extend((f"  data16 lea {node.var.name}@tlsgd(%rip), %rdi",
                                          "  .value 0x6666", "  rex64", "  call __tls_get_addr@PLT"))
                else:
                    self.assembly.append(f"  mov {node.var.name}@GOTPCREL(%rip), %rax")
            elif node.var.is_tls:
                self.assembly.extend(("  mov %fs:0, %rax",
                                      f"  add ${node.var.name}@tpoff, %rax"))
            elif node.ty.kind == "FUNC" and not node.var.is_definition:
                self.assembly.append(f"  mov {node.var.name}@GOTPCREL(%rip), %rax")
            else:
                self.assembly.append(f"  lea {node.var.name}(%rip), %rax")
            return
        if node.kind == "VLA_PTR":
            self.assembly.append(f"  lea {node.var.offset}(%rbp), %rax")
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
        if node.kind == "FUNCALL" and node.ret_buffer is not None:
            self.gen_expr(node)
            return
        raise CompileError(node.tok, "not an lvalue")

    def load(self, ty):
        if ty.kind in ("ARRAY", "STRUCT", "UNION", "FUNC", "VLA"):
            return
        if ty.kind in ("FLOAT", "DOUBLE"):
            instruction = "movss" if ty.kind == "FLOAT" else "movsd"
            self.assembly.append(f"  {instruction} (%rax), %xmm0")
            return
        if ty.kind == "LDOUBLE":
            self.assembly.append("  fldt (%rax)")
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
        if ty.kind == "LDOUBLE":
            self.assembly.append("  fstpt (%rdi)")
            return
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

    def store_gp(self, register, offset, size):
        registers = {1: ARGREG8, 2: ARGREG16, 4: ARGREG32, 8: ARGREG}
        if size in registers:
            self.assembly.append(f"  mov {registers[size][register]}, {offset}(%rbp)")
            return
        for i in range(size):
            self.assembly.extend((f"  mov {ARGREG8[register]}, {offset + i}(%rbp)",
                                  f"  shr $8, {ARGREG[register]}"))

    def store_fp(self, register, offset, size):
        instruction = "movss" if size == 4 else "movsd"
        self.assembly.append(f"  {instruction} %xmm{register}, {offset}(%rbp)")

    def push_args(self, node):
        args = node.args
        stack, gp, fp = 0, 0, 0
        if node.ret_buffer is not None and node.ty.size > 16:
            gp += 1
        for arg in args:
            ty = arg.ty
            arg.pass_by_stack = False
            if ty.kind in ("STRUCT", "UNION"):
                if ty.size <= 16:
                    fp1, fp2 = has_flonum(ty, 0, 8), has_flonum(ty, 8, 16)
                    if fp + fp1 + fp2 < FP_MAX and gp + (not fp1) + (not fp2) < GP_MAX:
                        fp += fp1 + fp2
                        gp += (not fp1) + (not fp2)
                        continue
                arg.pass_by_stack = True
                stack += align_to(ty.size, 8) // 8
            elif ty.kind in ("FLOAT", "DOUBLE"):
                arg.pass_by_stack = fp >= FP_MAX
                fp += 1
                stack += arg.pass_by_stack
            elif ty.kind == "LDOUBLE":
                arg.pass_by_stack = True
                stack += 2
            else:
                arg.pass_by_stack = gp >= GP_MAX
                gp += 1
                stack += arg.pass_by_stack
        if (self.depth + stack) % 2:
            self.assembly.append("  sub $8, %rsp")
            self.depth += 1
            stack += 1
        for pass_by_stack in (True, False):
            for arg in reversed(args):
                if arg.pass_by_stack != pass_by_stack:
                    continue
                self.gen_expr(arg)
                if arg.ty.kind in ("STRUCT", "UNION"):
                    size = align_to(arg.ty.size, 8)
                    self.assembly.append(f"  sub ${size}, %rsp")
                    self.depth += size // 8
                    for offset in range(arg.ty.size):
                        self.assembly.extend((f"  mov {offset}(%rax), %r10b",
                                              f"  mov %r10b, {offset}(%rsp)"))
                elif arg.ty.kind in ("FLOAT", "DOUBLE"):
                    self.pushf()
                elif arg.ty.kind == "LDOUBLE":
                    self.assembly.extend(("  sub $16, %rsp", "  fstpt (%rsp)"))
                    self.depth += 2
                else:
                    self.push()
        if node.ret_buffer is not None and node.ty.size > 16:
            self.assembly.append(f"  lea {node.ret_buffer.offset}(%rbp), %rax")
            self.push()
        return stack

    def copy_ret_buffer(self, var):
        ty = var.ty
        gp, fp = 0, 0
        if has_flonum(ty, 0, 8):
            self.store_fp(fp, var.offset, min(8, ty.size))
            fp += 1
        else:
            for i in range(min(8, ty.size)):
                self.assembly.extend((f"  mov %al, {var.offset + i}(%rbp)",
                                      "  shr $8, %rax"))
            gp += 1
        if ty.size > 8:
            if has_flonum(ty, 8, 16):
                self.store_fp(fp, var.offset + 8, ty.size - 8)
            else:
                small, full = ("%al", "%rax") if gp == 0 else ("%dl", "%rdx")
                for i in range(8, min(16, ty.size)):
                    self.assembly.extend((f"  mov {small}, {var.offset + i}(%rbp)",
                                          f"  shr $8, {full}"))

    def copy_struct_reg(self):
        ty = self.current_fn.ty.return_ty
        gp, fp = 0, 0
        self.assembly.append("  mov %rax, %rdi")
        if has_flonum(ty, 0, 8):
            instruction = "movss" if ty.size == 4 else "movsd"
            self.assembly.append(f"  {instruction} (%rdi), %xmm0")
            fp += 1
        else:
            self.assembly.append("  mov $0, %rax")
            for i in reversed(range(min(8, ty.size))):
                self.assembly.extend(("  shl $8, %rax", f"  mov {i}(%rdi), %al"))
            gp += 1
        if ty.size > 8:
            if has_flonum(ty, 8, 16):
                instruction = "movss" if ty.size == 4 else "movsd"
                self.assembly.append(f"  {instruction} 8(%rdi), %xmm{fp}")
            else:
                small, full = ("%al", "%rax") if gp == 0 else ("%dl", "%rdx")
                self.assembly.append(f"  mov $0, {full}")
                for i in reversed(range(8, min(16, ty.size))):
                    self.assembly.extend((f"  shl $8, {full}", f"  mov {i}(%rdi), {small}"))

    def copy_struct_mem(self):
        ty = self.current_fn.ty.return_ty
        var = self.current_fn.params[0]
        self.assembly.append(f"  mov {var.offset}(%rbp), %rdi")
        for i in range(ty.size):
            self.assembly.extend((f"  mov {i}(%rax), %dl", f"  mov %dl, {i}(%rdi)"))

    def cmp_zero(self, ty):
        if ty.kind == "LDOUBLE":
            self.assembly.extend(("  fldz", "  fucomip", "  fstp %st(0)"))
            return
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
        if from_ty.kind == "LDOUBLE":
            source = 10
        if to_ty.kind == "LDOUBLE":
            target = 10
        instruction = CAST_TABLE[source][target]
        if instruction is not None:
            self.assembly.extend("  " + part for part in instruction.split("; "))

    def builtin_alloca(self):
        offset = self.current_fn.alloca_bottom.offset
        self.assembly.extend((
            "  add $15, %rdi", "  and $0xfffffff0, %edi",
            f"  mov {offset}(%rbp), %rcx", "  sub %rsp, %rcx",
            "  mov %rsp, %rax", "  sub %rdi, %rsp", "  mov %rsp, %rdx",
            "1:", "  cmp $0, %rcx", "  je 2f", "  mov (%rax), %r8b",
            "  mov %r8b, (%rdx)", "  inc %rdx", "  inc %rax", "  dec %rcx",
            "  jmp 1b", "2:", f"  mov {offset}(%rbp), %rax", "  sub %rdi, %rax",
            f"  mov %rax, {offset}(%rbp)",
        ))

    def gen_expr(self, node):
        if node.tok is not None:
            file_no = node.tok.file.file_no if node.tok.file else 1
            self.assembly.append(f"  .loc {file_no} {node.tok.line_no}")
        if node.kind == "NULL_EXPR":
            return
        if node.kind == "LABEL_VAL":
            self.assembly.append(f"  lea {node.unique_label}(%rip), %rax")
            return
        if node.kind == "CAS":
            size = node.cas_addr.ty.base.size
            if size not in (1, 2, 4, 8):
                raise CompileError(node.tok, "unsupported atomic operand size")
            self.gen_expr(node.cas_addr)
            self.push()
            self.gen_expr(node.cas_new)
            self.push()
            self.gen_expr(node.cas_old)
            self.assembly.append("  mov %rax, %r8")
            self.load(node.cas_old.ty.base)
            self.pop("%rdx")
            self.pop("%rdi")
            self.assembly.extend((f"  lock cmpxchg {reg_dx(size)}, (%rdi)",
                                  "  sete %cl", "  je 1f",
                                  f"  mov {reg_ax(size)}, (%r8)", "1:",
                                  "  movzbl %cl, %eax"))
            return
        if node.kind == "MEMZERO":
            self.assembly.extend((f"  mov ${node.var.ty.size}, %rcx",
                                  f"  lea {node.var.offset}(%rbp), %rdi",
                                  "  mov $0, %al", "  rep stosb"))
            return
        if node.kind == "NUM":
            if node.ty.kind == "LDOUBLE":
                data = long_double_bytes(node.fvalue)
                lo, hi = int.from_bytes(data[:8], "little"), int.from_bytes(data[8:], "little")
                self.assembly.extend((f"  mov ${lo}, %rax  # long double",
                                      "  mov %rax, -16(%rsp)", f"  mov ${hi}, %rax",
                                      "  mov %rax, -8(%rsp)", "  fldt -16(%rsp)"))
                return
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
            if node.ty.kind == "LDOUBLE":
                self.assembly.append("  fchs")
                return
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
            if node.kind == "MEMBER" and node.member.is_bitfield:
                member = node.member
                self.assembly.append(f"  shl ${64 - member.bit_width - member.bit_offset}, %rax")
                shift = "shr" if member.ty.is_unsigned else "sar"
                self.assembly.append(f"  {shift} ${64 - member.bit_width}, %rax")
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
            if node.lhs.kind == "MEMBER" and node.lhs.member.is_bitfield:
                member = node.lhs.member
                self.assembly.append("  mov %rax, %r8")
                mask = ((1 << member.bit_width) - 1) << member.bit_offset
                self.assembly.extend(("  mov %rax, %rdi",
                                      f"  and ${(1 << member.bit_width) - 1}, %rdi",
                                      f"  shl ${member.bit_offset}, %rdi",
                                      "  mov (%rsp), %rax"))
                self.load(member.ty)
                self.assembly.extend((f"  mov ${~mask}, %r9", "  and %r9, %rax",
                                      "  or %rdi, %rax"))
                self.store(node.ty)
                self.assembly.append("  mov %r8, %rax")
                return
            self.store(node.ty)
            return
        if node.kind == "FUNCALL":
            if node.lhs.kind == "VAR" and node.lhs.var.name == "alloca":
                self.gen_expr(node.args[0])
                self.assembly.append("  mov %rax, %rdi")
                self.builtin_alloca()
                return
            stack_args = self.push_args(node)
            self.gen_expr(node.lhs)
            gp, fp = 0, 0
            if node.ret_buffer is not None and node.ty.size > 16:
                self.pop(ARGREG[gp])
                gp += 1
            for arg in node.args:
                ty = arg.ty
                if ty.kind in ("STRUCT", "UNION"):
                    if ty.size > 16:
                        continue
                    fp1, fp2 = has_flonum(ty, 0, 8), has_flonum(ty, 8, 16)
                    if fp + fp1 + fp2 < FP_MAX and gp + (not fp1) + (not fp2) < GP_MAX:
                        if fp1:
                            self.popf(fp)
                            fp += 1
                        else:
                            self.pop(ARGREG[gp])
                            gp += 1
                        if ty.size > 8:
                            if fp2:
                                self.popf(fp)
                                fp += 1
                            else:
                                self.pop(ARGREG[gp])
                                gp += 1
                elif ty.kind in ("FLOAT", "DOUBLE"):
                    if fp < FP_MAX:
                        self.popf(fp)
                        fp += 1
                elif ty.kind == "LDOUBLE":
                    continue
                else:
                    if gp < GP_MAX:
                        self.pop(ARGREG[gp])
                        gp += 1
            self.assembly.extend(("  mov %rax, %r10", f"  mov ${fp}, %rax",
                                  "  call *%r10", f"  add ${stack_args * 8}, %rsp"))
            self.depth -= stack_args
            if node.ty.kind == "BOOL":
                self.assembly.append("  movzx %al, %eax")
            elif node.ty.kind == "CHAR":
                instruction = "movzbl" if node.ty.is_unsigned else "movsbl"
                self.assembly.append(f"  {instruction} %al, %eax")
            elif node.ty.kind == "SHORT":
                instruction = "movzwl" if node.ty.is_unsigned else "movswl"
                self.assembly.append(f"  {instruction} %ax, %eax")
            if node.ret_buffer is not None and node.ty.size <= 16:
                self.copy_ret_buffer(node.ret_buffer)
                self.assembly.append(f"  lea {node.ret_buffer.offset}(%rbp), %rax")
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

        if node.lhs.ty.kind == "LDOUBLE":
            self.gen_expr(node.lhs)
            self.gen_expr(node.rhs)
            if node.kind in ("+", "-", "*", "/"):
                instruction = {"+": "faddp", "-": "fsubrp", "*": "fmulp", "/": "fdivrp"}[node.kind]
                self.assembly.append("  " + instruction)
                return
            if node.kind in ("==", "!=", "<", "<="):
                instruction = {"==": "sete", "!=": "setne", "<": "seta", "<=": "setae"}[node.kind]
                self.assembly.extend(("  fcomip", "  fstp %st(0)", f"  {instruction} %al", "  movzb %al, %rax"))
                return
            raise CompileError(node.tok, "invalid expression")

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
            file_no = node.tok.file.file_no if node.tok.file else 1
            self.assembly.append(f"  .loc {file_no} {node.tok.line_no}")
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
                if case.begin == case.end:
                    self.assembly.extend((f"  cmp ${case.begin}, {register}", f"  je {case.label}"))
                else:
                    di = "%rdi" if node.cond.ty.size == 8 else "%edi"
                    self.assembly.extend((f"  mov {register}, {di}", f"  sub ${case.begin}, {di}",
                                          f"  cmp ${case.end - case.begin}, {di}", f"  jbe {case.label}"))
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
                if node.lhs.ty.kind in ("STRUCT", "UNION"):
                    if node.lhs.ty.size <= 16:
                        self.copy_struct_reg()
                    else:
                        self.copy_struct_mem()
            self.assembly.append(f"  jmp .L.return.{self.current_fn.name}")
            return
        if node.kind == "GOTO_EXPR":
            self.gen_expr(node.lhs)
            self.assembly.append("  jmp *%rax")
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
        if node.kind == "ASM":
            self.assembly.append("  " + node.asm_str)
            return
        raise CompileError(node.tok, "invalid statement")

    def generate(self, program, files=()):
        self.assembly = []
        for file in files:
            name = file.name.replace("\\", "\\\\").replace('"', '\\"')
            self.assembly.append(f'  .file {file.file_no} "{name}"')
        for var in program:
            if not var.is_function and var.is_definition:
                alignment = max(16, var.align) if var.ty.kind == "ARRAY" and var.ty.size >= 16 else var.align
                if var.is_tls:
                    section = '.section .tdata,"awT",@progbits' if var.init_data is not None else '.section .tbss,"awT",@nobits'
                else:
                    section = ".data" if var.init_data is not None else ".bss"
                visibility = ".local" if var.is_static else ".globl"
                self.assembly.append(f"  {visibility} {var.name}")
                if self.fcommon and var.is_tentative:
                    self.assembly.append(f"  .comm {var.name}, {var.ty.size}, {alignment}")
                    continue
                self.assembly.append(f"  {section}")
                if var.init_data is not None:
                    self.assembly.extend((f"  .type {var.name}, @object", f"  .size {var.name}, {var.ty.size}"))
                self.assembly.extend((f"  .align {alignment}", f"{var.name}:"))
                if var.init_data is not None:
                    relocations = {rel.offset: rel for rel in var.relocations}
                    position = 0
                    while position < var.ty.size:
                        if position in relocations:
                            rel = relocations[position]
                            label = rel.label if isinstance(rel.label, str) else rel.label.unique_label
                            self.assembly.append(f"  .quad {label}{rel.addend:+d}")
                            position += 8
                        else:
                            self.assembly.append(f"  .byte {var.init_data[position]}")
                            position += 1
                else:
                    self.assembly.append(f"  .zero {var.ty.size}")
        for function in program:
            if not function.is_function or not function.is_definition:
                continue
            if not function.is_live:
                continue
            top, gp, fp = 16, 0, 0
            for var in function.params:
                ty = var.ty
                if ty.kind in ("STRUCT", "UNION"):
                    on_stack = True
                    if ty.size <= 16:
                        fp1 = has_flonum(ty, 0, 8)
                        fp2 = has_flonum(ty, 8, 16, 8)
                        if fp + fp1 + fp2 < FP_MAX and gp + (not fp1) + (not fp2) < GP_MAX:
                            fp += fp1 + fp2
                            gp += (not fp1) + (not fp2)
                            on_stack = False
                elif ty.kind in ("FLOAT", "DOUBLE"):
                    on_stack = fp >= FP_MAX
                    fp += 1
                elif ty.kind == "LDOUBLE":
                    on_stack = True
                else:
                    on_stack = gp >= GP_MAX
                    gp += 1
                if on_stack:
                    top = align_to(top, 8)
                    var.offset = top
                    top += var.ty.size
            offset = 0
            for var in function.locals:
                if var.offset > 0:
                    continue
                offset += var.ty.size
                alignment = max(16, var.align) if var.ty.kind == "ARRAY" and var.ty.size >= 16 else var.align
                offset = align_to(offset, alignment)
                var.offset = -offset
            function.stack_size = align_to(offset, 16)
            self.current_fn = function
            directive = ".local" if function.is_static else ".globl"
            self.assembly.extend([f"  {directive} {function.name}", "  .text", f"  .type {function.name}, @function", f"{function.name}:",
                                  "  push %rbp", "  mov %rsp, %rbp",
                                  f"  sub ${function.stack_size}, %rsp"])
            self.assembly.append(f"  mov %rsp, {function.alloca_bottom.offset}(%rbp)")
            if function.va_area is not None:
                offset = function.va_area.offset
                fp_count = sum(var.ty.kind in ("FLOAT", "DOUBLE") for var in function.params)
                gp_count = len(function.params) - fp_count
                self.assembly.extend((f"  movl ${gp_count * 8}, {offset}(%rbp)",
                                      f"  movl ${48 + fp_count * 8}, {offset + 4}(%rbp)",
                                      f"  movq %rbp, {offset + 8}(%rbp)",
                                      f"  addq $16, {offset + 8}(%rbp)",
                                      f"  movq %rbp, {offset + 16}(%rbp)",
                                      f"  addq ${offset + 24}, {offset + 16}(%rbp)"))
                for index, register in enumerate(ARGREG):
                    self.assembly.append(f"  movq {register}, {offset + 24 + index * 8}(%rbp)")
                for index in range(8):
                    self.assembly.append(f"  movsd %xmm{index}, {offset + 72 + index * 8}(%rbp)")
            gp, fp = 0, 0
            for var in function.params:
                if var.offset > 0:
                    continue
                ty = var.ty
                if ty.kind in ("STRUCT", "UNION"):
                    assert ty.size <= 16
                    if has_flonum(ty, 0, 8):
                        self.store_fp(fp, var.offset, min(8, ty.size))
                        fp += 1
                    else:
                        self.store_gp(gp, var.offset, min(8, ty.size))
                        gp += 1
                    if ty.size > 8:
                        if has_flonum(ty, 8, 16):
                            self.store_fp(fp, var.offset + 8, ty.size - 8)
                            fp += 1
                        else:
                            self.store_gp(gp, var.offset + 8, ty.size - 8)
                            gp += 1
                elif ty.kind in ("FLOAT", "DOUBLE"):
                    if fp >= 8:
                        raise CompileError(var.ty.name, "at most 8 floating parameters are supported")
                    self.store_fp(fp, var.offset, ty.size)
                    fp += 1
                else:
                    if gp >= len(ARGREG):
                        raise CompileError(var.ty.name, "at most 6 parameters are supported")
                    self.store_gp(gp, var.offset, ty.size)
                    gp += 1
            self.gen_stmt(function.body)
            assert self.depth == 0
            if function.name == "main":
                self.assembly.append("  mov $0, %rax")
            self.assembly.extend([f".L.return.{function.name}:", "  mov %rbp, %rsp",
                                  "  pop %rbp", "  ret"])
        return "\n".join(self.assembly)


def codegen(program, files=(), fcommon=True, fpic=False):
    return CodeGenerator(fcommon, fpic).generate(program, files)
