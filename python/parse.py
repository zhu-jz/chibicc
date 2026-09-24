"""Build a list of expression statements from tokens.

Based on chibicc commit 1f9f3adf324af1432a380b41c7690834e649e346.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError, Node


# Each parser function returns (node, next unconsumed token index).
# expr = assign
def expr(tokens, position):
    return assign(tokens, position)


# assign = equality ("=" assign)?
def assign(tokens, position):
    node, position = equality(tokens, position)
    if tokens[position].text == "=":
        rhs, position = assign(tokens, position + 1)
        node = Node("ASSIGN", node, rhs)
    return node, position


# equality = relational (("==" | "!=") relational)*
def equality(tokens, position):
    node, position = relational(tokens, position)
    while tokens[position].text in ("==", "!="):
        operator = tokens[position].text
        rhs, position = relational(tokens, position + 1)
        node = Node(operator, node, rhs)
    return node, position


# relational = add (("<" | "<=" | ">" | ">=") add)*
def relational(tokens, position):
    node, position = add(tokens, position)
    while tokens[position].text in ("<", "<=", ">", ">="):
        operator = tokens[position].text
        rhs, position = add(tokens, position + 1)
        if operator == ">":
            node = Node("<", rhs, node)
        elif operator == ">=":
            node = Node("<=", rhs, node)
        else:
            node = Node(operator, node, rhs)
    return node, position


# add = mul (("+" | "-") mul)*
def add(tokens, position):
    node, position = mul(tokens, position)
    while tokens[position].text in ("+", "-"):
        operator = tokens[position].text
        rhs, position = mul(tokens, position + 1)
        node = Node(operator, node, rhs)
    return node, position


# mul = unary (("*" | "/") unary)*
def mul(tokens, position):
    node, position = unary(tokens, position)
    while tokens[position].text in ("*", "/"):
        operator = tokens[position].text
        rhs, position = unary(tokens, position + 1)
        node = Node(operator, node, rhs)
    return node, position


# unary = ("+" | "-") unary | primary
def unary(tokens, position):
    operator = tokens[position].text
    if operator == "+":
        return unary(tokens, position + 1)
    if operator == "-":
        operand, position = unary(tokens, position + 1)
        return Node("NEG", lhs=operand), position
    return primary(tokens, position)


# primary = "(" expr ")" | identifier | number
def primary(tokens, position):
    token = tokens[position]
    if token.text == "(":
        node, position = expr(tokens, position + 1)
        if tokens[position].text != ")":
            raise CompileError(tokens[position].position, "expected ')'")
        return node, position + 1

    if token.kind == "IDENT":
        return Node("VAR", name=token.text), position + 1

    if token.kind == "NUM":
        return Node("NUM", value=token.value), position + 1

    raise CompileError(token.position, "expected an expression")


# stmt = expr-stmt
def stmt(tokens, position):
    return expr_stmt(tokens, position)


# expr-stmt = expr ";"
def expr_stmt(tokens, position):
    node, position = expr(tokens, position)
    if tokens[position].text != ";":
        raise CompileError(tokens[position].position, "expected ';'")
    return Node("EXPR_STMT", lhs=node), position + 1


# program = stmt*
def parse(tokens):
    statements = []
    position = 0
    while tokens[position].kind != "EOF":
        node, position = stmt(tokens, position)
        statements.append(node)
    return statements
