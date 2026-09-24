"""Generate x86-64 Linux assembly from an expression tree.

Based on chibicc commit 725badfb494544b7c7f1d4c4690b9bc033c6d051.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""


class CodeGenerator:
    def __init__(self):
        self.assembly = ["  .globl main", "main:"]
        self.depth = 0

    def push(self):
        self.assembly.append("  push %rax")
        self.depth += 1

    def pop(self, register):
        self.assembly.append(f"  pop {register}")
        self.depth -= 1

    def gen_expr(self, node):
        if node.kind == "NUM":
            self.assembly.append(f"  mov ${node.value}, %rax")
            return
        if node.kind == "NEG":
            self.gen_expr(node.lhs)
            self.assembly.append("  neg %rax")
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

    def generate(self, node):
        self.gen_expr(node)
        self.assembly.append("  ret")
        assert self.depth == 0
        return "\n".join(self.assembly)


def codegen(node):
    return CodeGenerator().generate(node)
