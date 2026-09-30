"""Allocate local stack slots and generate x86-64 Linux assembly.

Based on chibicc commit 863e2b8de25fdf43a4a63b93d0f57718e9edaa47.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


from common import CompileError


ARGREG = ("%rdi", "%rsi", "%rdx", "%rcx", "%r8", "%r9")
ARGREG8 = ("%dil", "%sil", "%dl", "%cl", "%r8b", "%r9b")


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
        if ty.kind == "ARRAY":
            return
        if ty.size == 1:
            self.assembly.append("  movsbq (%rax), %rax")
        else:
            self.assembly.append("  mov (%rax), %rax")

    def store(self, ty):
        self.pop("%rdi")
        if ty.size == 1:
            self.assembly.append("  mov %al, (%rdi)")
        else:
            self.assembly.append("  mov %rax, (%rdi)")

    def gen_expr(self, node):
        if node.tok is not None:
            self.assembly.append(f"  .loc 1 {node.tok.line_no}")
        if node.kind == "NUM":
            self.assembly.append(f"  mov ${node.value}, %rax")
            return
        if node.kind == "NEG":
            self.gen_expr(node.lhs)
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
            if len(node.args) > len(ARGREG):
                raise CompileError(node.tok, "at most 6 arguments are supported")
            for arg in node.args:
                self.gen_expr(arg)
                self.push()
            for index in range(len(node.args) - 1, -1, -1):
                self.pop(ARGREG[index])
            self.assembly.append("  mov $0, %rax")
            self.assembly.append(f"  call {node.funcname}")
            return
        if node.kind == "STMT_EXPR":
            for statement in node.body:
                self.gen_stmt(statement)
            return
        if node.kind == "COMMA":
            self.gen_expr(node.lhs)
            self.gen_expr(node.rhs)
            return

        # Save the right result, compute the left, then restore the right.
        self.gen_expr(node.rhs)
        self.push()
        self.gen_expr(node.lhs)
        self.pop("%rdi")

        if node.kind == "+":
            self.assembly.append("  add %rdi, %rax")
        elif node.kind == "-":
            self.assembly.append("  sub %rdi, %rax")
        elif node.kind == "*":
            self.assembly.append("  imul %rdi, %rax")
        elif node.kind == "/":
            self.assembly.append("  cqo")
            self.assembly.append("  idiv %rdi")
        elif node.kind in ("==", "!=", "<", "<="):
            instructions = {
                "==": "sete", "!=": "setne", "<": "setl", "<=": "setle",
            }
            self.assembly.append("  cmp %rdi, %rax")
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
            self.assembly.append("  cmp $0, %rax")
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
                self.assembly.append("  cmp $0, %rax")
                self.assembly.append(f"  je  .L.end.{label}")
            self.gen_stmt(node.then)
            if node.inc is not None:
                self.gen_expr(node.inc)
            self.assembly.append(f"  jmp .L.begin.{label}")
            self.assembly.append(f".L.end.{label}:")
            return
        if node.kind == "BLOCK":
            for statement in node.body:
                self.gen_stmt(statement)
            return
        if node.kind == "RETURN":
            self.gen_expr(node.lhs)
            self.assembly.append(f"  jmp .L.return.{self.current_fn.name}")
            return
        if node.kind == "EXPR_STMT":
            self.gen_expr(node.lhs)
            return
        raise CompileError(node.tok, "invalid statement")

    def generate(self, program):
        self.assembly = []
        for var in program:
            if not var.is_function:
                self.assembly.extend(["  .data", f"  .globl {var.name}", f"{var.name}:"])
                if var.init_data is not None:
                    for value in var.init_data:
                        self.assembly.append(f"  .byte {value}")
                else:
                    self.assembly.append(f"  .zero {var.ty.size}")
        for function in program:
            if not function.is_function:
                continue
            offset = 0
            for var in function.locals:
                offset += var.ty.size
                var.offset = -offset
            function.stack_size = (offset + 15) // 16 * 16
            self.current_fn = function
            self.assembly.extend([f"  .globl {function.name}", "  .text", f"{function.name}:",
                                  "  push %rbp", "  mov %rsp, %rbp",
                                  f"  sub ${function.stack_size}, %rsp"])
            if len(function.params) > len(ARGREG):
                raise CompileError(function.params[6].ty.name,
                                   "at most 6 parameters are supported")
            for index, var in enumerate(function.params):
                register = ARGREG8[index] if var.ty.size == 1 else ARGREG[index]
                self.assembly.append(f"  mov {register}, {var.offset}(%rbp)")
            self.gen_stmt(function.body)
            assert self.depth == 0
            self.assembly.extend([f".L.return.{function.name}:", "  mov %rbp, %rsp",
                                  "  pop %rbp", "  ret"])
        return "\n".join(self.assembly)


def codegen(program):
    return CodeGenerator().generate(program)
