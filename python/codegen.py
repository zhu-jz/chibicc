"""Allocate local stack slots and generate x86-64 Linux assembly.

Based on chibicc commit 863e2b8de25fdf43a4a63b93d0f57718e9edaa47.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


from common import CompileError


class CodeGenerator:
    def __init__(self):
        self.assembly = []
        self.depth = 0
        self.label_count = 0

    def push(self):
        self.assembly.append("  push %rax")
        self.depth += 1

    def pop(self, register):
        self.assembly.append(f"  pop {register}")
        self.depth -= 1

    def gen_addr(self, node):
        if node.kind == "VAR":
            self.assembly.append(f"  lea {node.var.offset}(%rbp), %rax")
            return
        if node.kind == "DEREF":
            self.gen_expr(node.lhs)
            return
        raise CompileError(node.tok.position, "not an lvalue")

    def gen_expr(self, node):
        if node.kind == "NUM":
            self.assembly.append(f"  mov ${node.value}, %rax")
            return
        if node.kind == "NEG":
            self.gen_expr(node.lhs)
            self.assembly.append("  neg %rax")
            return
        if node.kind == "VAR":
            self.gen_addr(node)
            self.assembly.append("  mov (%rax), %rax")
            return
        if node.kind == "DEREF":
            self.gen_expr(node.lhs)
            self.assembly.append("  mov (%rax), %rax")
            return
        if node.kind == "ADDR":
            self.gen_addr(node.lhs)
            return
        if node.kind == "ASSIGN":
            self.gen_addr(node.lhs)
            self.push()
            self.gen_expr(node.rhs)
            self.pop("%rdi")
            self.assembly.append("  mov %rax, (%rdi)")
            return
        if node.kind == "FUNCALL":
            self.assembly.append("  mov $0, %rax")
            self.assembly.append(f"  call {node.funcname}")
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
            raise CompileError(node.tok.position, "invalid expression")

    def gen_stmt(self, node):
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
            self.assembly.append("  jmp .L.return")
            return
        if node.kind == "EXPR_STMT":
            self.gen_expr(node.lhs)
            return
        raise CompileError(node.tok.position, "invalid statement")

    def generate(self, program):
        offset = 0
        for var in program.locals:
            offset += 8
            var.offset = -offset
        program.stack_size = (offset + 15) // 16 * 16

        self.assembly = ["  .globl main", "main:", "  push %rbp",
                         "  mov %rsp, %rbp", f"  sub ${program.stack_size}, %rsp"]
        self.gen_stmt(program.body)
        assert self.depth == 0
        self.assembly.extend([".L.return:", "  mov %rbp, %rsp", "  pop %rbp", "  ret"])
        return "\n".join(self.assembly)


def codegen(program):
    return CodeGenerator().generate(program)
