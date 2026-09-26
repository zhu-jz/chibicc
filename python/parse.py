"""Build a function containing statements and local variables.

Based on chibicc commit 18ac283a5d19c19f1e1a7020a50fe34c2160a0f8.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError, Function, Node, Obj


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.locals = []

    def find_var(self, name):
        for var in self.locals:
            if var.name == name:
                return var
        return None

    # Each parser function returns (node, next unconsumed token index).
    # expr = assign
    def expr(self, position):
        return self.assign(position)

    # assign = equality ("=" assign)?
    def assign(self, position):
        node, position = self.equality(position)
        if self.tokens[position].text == "=":
            rhs, position = self.assign(position + 1)
            node = Node("ASSIGN", node, rhs)
        return node, position

    # equality = relational (("==" | "!=") relational)*
    def equality(self, position):
        node, position = self.relational(position)
        while self.tokens[position].text in ("==", "!="):
            operator = self.tokens[position].text
            rhs, position = self.relational(position + 1)
            node = Node(operator, node, rhs)
        return node, position

    # relational = add (("<" | "<=" | ">" | ">=") add)*
    def relational(self, position):
        node, position = self.add(position)
        while self.tokens[position].text in ("<", "<=", ">", ">="):
            operator = self.tokens[position].text
            rhs, position = self.add(position + 1)
            if operator == ">":
                node = Node("<", rhs, node)
            elif operator == ">=":
                node = Node("<=", rhs, node)
            else:
                node = Node(operator, node, rhs)
        return node, position

    # add = mul (("+" | "-") mul)*
    def add(self, position):
        node, position = self.mul(position)
        while self.tokens[position].text in ("+", "-"):
            operator = self.tokens[position].text
            rhs, position = self.mul(position + 1)
            node = Node(operator, node, rhs)
        return node, position

    # mul = unary (("*" | "/") unary)*
    def mul(self, position):
        node, position = self.unary(position)
        while self.tokens[position].text in ("*", "/"):
            operator = self.tokens[position].text
            rhs, position = self.unary(position + 1)
            node = Node(operator, node, rhs)
        return node, position

    # unary = ("+" | "-") unary | primary
    def unary(self, position):
        operator = self.tokens[position].text
        if operator == "+":
            return self.unary(position + 1)
        if operator == "-":
            operand, position = self.unary(position + 1)
            return Node("NEG", lhs=operand), position
        return self.primary(position)

    # primary = "(" expr ")" | identifier | number
    def primary(self, position):
        token = self.tokens[position]
        if token.text == "(":
            node, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position].position, "expected ')'")
            return node, position + 1

        if token.kind == "IDENT":
            var = self.find_var(token.text)
            if var is None:
                var = Obj(token.text)
                self.locals.insert(0, var)
            return Node("VAR", var=var), position + 1

        if token.kind == "NUM":
            return Node("NUM", value=token.value), position + 1

        raise CompileError(token.position, "expected an expression")

    # stmt = "return" expr ";" | "{" compound-stmt | expr-stmt
    def stmt(self, position):
        if self.tokens[position].text == "return":
            node, position = self.expr(position + 1)
            if self.tokens[position].text != ";":
                raise CompileError(self.tokens[position].position, "expected ';'")
            return Node("RETURN", lhs=node), position + 1
        if self.tokens[position].text == "{":
            return self.compound_stmt(position + 1)
        return self.expr_stmt(position)

    # compound-stmt = stmt* "}"
    def compound_stmt(self, position):
        statements = []
        while self.tokens[position].text != "}":
            node, position = self.stmt(position)
            statements.append(node)
        return Node("BLOCK", body=statements), position + 1

    # expr-stmt = expr ";"
    def expr_stmt(self, position):
        node, position = self.expr(position)
        if self.tokens[position].text != ";":
            raise CompileError(self.tokens[position].position, "expected ';'")
        return Node("EXPR_STMT", lhs=node), position + 1

    # program = "{" compound-stmt
    def parse(self):
        if self.tokens[0].text != "{":
            raise CompileError(self.tokens[0].position, "expected '{'")
        body, position = self.compound_stmt(1)
        # This original commit does not check for tokens after the outer block.
        return Function(body, self.locals)


def parse(tokens):
    return Parser(tokens).parse()
