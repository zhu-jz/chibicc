"""Build a function using recursive descent.

Each grammar function returns a node and the next token index. Python tuples
replace C's returned node plus output pointer for the remaining tokens.

Based on chibicc commit a6bc4ab101c20b6398fd6bbfe124665bb7db5d25.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError, Function, Node, Obj
from type import add_type, is_integer, ty_int


def new_add(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_integer(lhs.ty) and is_integer(rhs.ty):
        return Node("+", lhs, rhs, tok=token)
    if lhs.ty.base is not None and rhs.ty.base is not None:
        raise CompileError(token.position, "invalid operands")
    # Canonicalize integer + pointer to pointer + integer.
    if lhs.ty.base is None and rhs.ty.base is not None:
        lhs, rhs = rhs, lhs
    rhs = Node("*", rhs, Node("NUM", value=8, tok=token), tok=token)
    return Node("+", lhs, rhs, tok=token)


def new_sub(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_integer(lhs.ty) and is_integer(rhs.ty):
        return Node("-", lhs, rhs, tok=token)
    if lhs.ty.base is not None and is_integer(rhs.ty):
        rhs = Node("*", rhs, Node("NUM", value=8, tok=token), tok=token)
        add_type(rhs)
        return Node("-", lhs, rhs, tok=token, ty=lhs.ty)
    if lhs.ty.base is not None and rhs.ty.base is not None:
        difference = Node("-", lhs, rhs, tok=token, ty=ty_int)
        return Node("/", difference, Node("NUM", value=8, tok=token), tok=token)
    raise CompileError(token.position, "invalid operands")


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
            token = self.tokens[position]
            rhs, position = self.assign(position + 1)
            node = Node("ASSIGN", node, rhs, tok=token)
        return node, position

    # equality = relational (("==" | "!=") relational)*
    def equality(self, position):
        node, position = self.relational(position)
        while self.tokens[position].text in ("==", "!="):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.relational(position + 1)
            node = Node(operator, node, rhs, tok=token)
        return node, position

    # relational = add (("<" | "<=" | ">" | ">=") add)*
    def relational(self, position):
        node, position = self.add(position)
        while self.tokens[position].text in ("<", "<=", ">", ">="):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.add(position + 1)
            if operator == ">":
                node = Node("<", rhs, node, tok=token)
            elif operator == ">=":
                node = Node("<=", rhs, node, tok=token)
            else:
                node = Node(operator, node, rhs, tok=token)
        return node, position

    # add = mul (("+" | "-") mul)*
    def add(self, position):
        node, position = self.mul(position)
        while self.tokens[position].text in ("+", "-"):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.mul(position + 1)
            if operator == "+":
                node = new_add(node, rhs, token)
            else:
                node = new_sub(node, rhs, token)
        return node, position

    # mul = unary (("*" | "/") unary)*
    def mul(self, position):
        node, position = self.unary(position)
        while self.tokens[position].text in ("*", "/"):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.unary(position + 1)
            node = Node(operator, node, rhs, tok=token)
        return node, position

    # unary = ("+" | "-" | "*" | "&") unary | primary
    def unary(self, position):
        token = self.tokens[position]
        operator = self.tokens[position].text
        if operator == "+":
            return self.unary(position + 1)
        if operator == "-":
            operand, position = self.unary(position + 1)
            return Node("NEG", lhs=operand, tok=token), position
        if operator == "&":
            operand, position = self.unary(position + 1)
            return Node("ADDR", lhs=operand, tok=token), position
        if operator == "*":
            operand, position = self.unary(position + 1)
            return Node("DEREF", lhs=operand, tok=token), position
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
            return Node("VAR", var=var, tok=token), position + 1

        if token.kind == "NUM":
            return Node("NUM", value=token.value, tok=token), position + 1

        raise CompileError(token.position, "expected an expression")

    # stmt = "return" expr ";" | "{" compound-stmt | expr-stmt
    #      | "if" "(" expr ")" stmt ("else" stmt)?
    #      | "for" "(" expr-stmt expr? ";" expr? ")" stmt
    #      | "while" "(" expr ")" stmt
    def stmt(self, position):
        token = self.tokens[position]
        if self.tokens[position].text == "return":
            node, position = self.expr(position + 1)
            if self.tokens[position].text != ";":
                raise CompileError(self.tokens[position].position, "expected ';'")
            return Node("RETURN", lhs=node, tok=token), position + 1
        if self.tokens[position].text == "if":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position].position, "expected '('")
            cond, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position].position, "expected ')'")
            then, position = self.stmt(position + 1)
            els = None
            if self.tokens[position].text == "else":
                els, position = self.stmt(position + 1)
            return Node("IF", cond=cond, then=then, els=els, tok=token), position
        if self.tokens[position].text == "for":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position].position, "expected '('")
            init, position = self.expr_stmt(position + 1)
            cond = None
            if self.tokens[position].text != ";":
                cond, position = self.expr(position)
            if self.tokens[position].text != ";":
                raise CompileError(self.tokens[position].position, "expected ';'")
            position += 1
            inc = None
            if self.tokens[position].text != ")":
                inc, position = self.expr(position)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position].position, "expected ')'")
            then, position = self.stmt(position + 1)
            return Node("FOR", init=init, cond=cond, inc=inc, then=then, tok=token), position
        if self.tokens[position].text == "while":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position].position, "expected '('")
            cond, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position].position, "expected ')'")
            then, position = self.stmt(position + 1)
            return Node("FOR", cond=cond, then=then, tok=token), position
        if self.tokens[position].text == "{":
            return self.compound_stmt(position + 1)
        return self.expr_stmt(position)

    # compound-stmt = stmt* "}"
    def compound_stmt(self, position):
        token = self.tokens[position]
        statements = []
        while self.tokens[position].text != "}":
            node, position = self.stmt(position)
            add_type(node)
            statements.append(node)
        return Node("BLOCK", body=statements, tok=token), position + 1

    # expr-stmt = expr? ";"
    def expr_stmt(self, position):
        token = self.tokens[position]
        if self.tokens[position].text == ";":
            return Node("BLOCK", tok=token), position + 1
        node, position = self.expr(position)
        if self.tokens[position].text != ";":
            raise CompileError(self.tokens[position].position, "expected ';'")
        return Node("EXPR_STMT", lhs=node, tok=token), position + 1

    # program = "{" compound-stmt
    def parse(self):
        if self.tokens[0].text != "{":
            raise CompileError(self.tokens[0].position, "expected '{'")
        body, position = self.compound_stmt(1)
        # This original commit does not check for tokens after the outer block.
        return Function(body, self.locals)


def parse(tokens):
    return Parser(tokens).parse()
