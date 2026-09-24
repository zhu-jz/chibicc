"""Generate x86-64 Linux assembly from a list of statements.

Based on chibicc commit 1f9f3adf324af1432a380b41c7690834e649e346.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


from common import CompileError


class CodeGenerator:
    def __init__(self):
        self.assembly = ["  .globl main", "main:", "  push %rbp",
                         "  mov %rsp, %rbp", "  sub $208, %rsp"]
        self.depth = 0

    def push(self):
        self.assembly.append("  push %rax")
        self.depth += 1

    def pop(self, register):
        self.assembly.append(f"  pop {register}")
        self.depth -= 1

    def gen_addr(self, node):
        if node.kind != "VAR":
            raise CompileError(None, "not an lvalue")
        offset = (ord(node.name) - ord("a") + 1) * 8
        self.assembly.append(f"  lea {-offset}(%rbp), %rax")

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
        if node.kind == "ASSIGN":
            self.gen_addr(node.lhs)
            self.push()
            self.gen_expr(node.rhs)
            self.pop("%rdi")
            self.assembly.append("  mov %rax, (%rdi)")
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
            raise AssertionError("invalid expression")

    def gen_stmt(self, node):
        if node.kind == "EXPR_STMT":
            self.gen_expr(node.lhs)
            return
        raise AssertionError("invalid statement")

    def generate(self, statements):
        for node in statements:
            self.gen_stmt(node)
            assert self.depth == 0
        self.assembly.extend(["  mov %rbp, %rsp", "  pop %rbp", "  ret"])
        return "\n".join(self.assembly)


def codegen(statements):
    return CodeGenerator().generate(statements)
