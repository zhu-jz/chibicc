"""Build a function using recursive descent.

Each grammar function returns a node and the next token index. Python tuples
replace C's returned node plus output pointer for the remaining tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError, Member, Node, Obj, Scope, Type, align_to
from type import add_type, array_of, copy_type, func_type, is_integer, pointer_to, ty_char, ty_short, ty_int, ty_long


def new_add(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_integer(lhs.ty) and is_integer(rhs.ty):
        return Node("+", lhs, rhs, tok=token)
    if lhs.ty.base is not None and rhs.ty.base is not None:
        raise CompileError(token, "invalid operands")
    # Canonicalize integer + pointer to pointer + integer.
    if lhs.ty.base is None and rhs.ty.base is not None:
        lhs, rhs = rhs, lhs
    rhs = Node("*", rhs, Node("NUM", value=lhs.ty.base.size, tok=token), tok=token)
    return Node("+", lhs, rhs, tok=token)


def new_sub(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_integer(lhs.ty) and is_integer(rhs.ty):
        return Node("-", lhs, rhs, tok=token)
    if lhs.ty.base is not None and is_integer(rhs.ty):
        rhs = Node("*", rhs, Node("NUM", value=lhs.ty.base.size, tok=token), tok=token)
        add_type(rhs)
        return Node("-", lhs, rhs, tok=token, ty=lhs.ty)
    if lhs.ty.base is not None and rhs.ty.base is not None:
        difference = Node("-", lhs, rhs, tok=token, ty=ty_int)
        return Node("/", difference, Node("NUM", value=lhs.ty.base.size, tok=token), tok=token)
    raise CompileError(token, "invalid operands")


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.locals = []
        self.globals = []
        self.unique_id = 0
        self.scopes = [Scope()]  # Global scope, followed by nested block scopes.

    def enter_scope(self):
        self.scopes.append(Scope())

    def leave_scope(self):
        self.scopes.pop()

    def new_lvar(self, name, ty):
        var = Obj(name, ty=ty, is_local=True)
        self.locals.insert(0, var)
        self.scopes[-1].vars.insert(0, var)
        return var

    def new_gvar(self, name, ty):
        var = Obj(name, ty=ty)
        self.globals.insert(0, var)
        self.scopes[-1].vars.insert(0, var)
        return var

    def new_string_literal(self, data, ty):
        var = self.new_gvar(f".L..{self.unique_id}", ty)
        self.unique_id += 1
        var.init_data = data
        return var

    def find_var(self, name):
        for scope in reversed(self.scopes):
            for var in scope.vars:
                if var.name == name:
                    return var
        return None

    def find_tag(self, name):
        for scope in reversed(self.scopes):
            if name in scope.tags:
                return scope.tags[name]
        return None

    # Each parser function returns (node, next unconsumed token index).
    # expr = assign ("," expr)?
    def expr(self, position):
        node, position = self.assign(position)
        if self.tokens[position].text == ",":
            token = self.tokens[position]
            rhs, position = self.expr(position + 1)
            node = Node("COMMA", node, rhs, tok=token)
        return node, position

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

    # unary = ("+" | "-" | "*" | "&") unary | postfix
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
        return self.postfix(position)

    def struct_ref(self, lhs, token):
        add_type(lhs)
        if lhs.ty.kind not in ("STRUCT", "UNION"):
            raise CompileError(lhs.tok, "not a struct nor a union")
        for member in lhs.ty.members:
            if member.name.text == token.text:
                return Node("MEMBER", lhs=lhs, member=member, tok=token)
        raise CompileError(token, "no such member")

    # postfix = primary ("[" expr "]" | "." identifier | "->" identifier)*
    def postfix(self, position):
        node, position = self.primary(position)
        while True:
            if self.tokens[position].text == "[":
                token = self.tokens[position]
                index, position = self.expr(position + 1)
                if self.tokens[position].text != "]":
                    raise CompileError(self.tokens[position], "expected ']'")
                node = Node("DEREF", lhs=new_add(node, index, token), tok=token)
                position += 1
            elif self.tokens[position].text == ".":
                node = self.struct_ref(node, self.tokens[position + 1])
                position += 2
            elif self.tokens[position].text == "->":
                node = Node("DEREF", lhs=node, tok=self.tokens[position])
                node = self.struct_ref(node, self.tokens[position + 1])
                position += 2
            else:
                return node, position

    # funcall = identifier "(" (assign ("," assign)*)? ")"
    def funcall(self, position):
        token = self.tokens[position]
        position += 2
        args = []
        while self.tokens[position].text != ")":
            if args:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            arg, position = self.assign(position)
            args.append(arg)
        return Node("FUNCALL", funcname=token.text, args=args, tok=token), position + 1

    # primary = "(" expr ")" | "sizeof" unary | identifier func-args? | number
    def primary(self, position):
        token = self.tokens[position]
        if token.text == "(" and self.tokens[position + 1].text == "{":
            block, position = self.compound_stmt(position + 2)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            return Node("STMT_EXPR", body=block.body, tok=token), position + 1
        if token.text == "(":
            node, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            return node, position + 1

        if token.text == "sizeof":
            operand, position = self.unary(position + 1)
            add_type(operand)
            return Node("NUM", value=operand.ty.size, tok=token), position

        if token.kind == "IDENT":
            if self.tokens[position + 1].text == "(":
                return self.funcall(position)
            var = self.find_var(token.text)
            if var is None:
                raise CompileError(token, "undefined variable")
            return Node("VAR", var=var, tok=token), position + 1

        if token.kind == "STR":
            var = self.new_string_literal(token.str, token.ty)
            return Node("VAR", var=var, tok=token), position + 1

        if token.kind == "NUM":
            return Node("NUM", value=token.value, tok=token), position + 1

        raise CompileError(token, "expected an expression")

    # stmt = "return" expr ";" | "{" compound-stmt | expr-stmt
    #      | "if" "(" expr ")" stmt ("else" stmt)?
    #      | "for" "(" expr-stmt expr? ";" expr? ")" stmt
    #      | "while" "(" expr ")" stmt
    def stmt(self, position):
        token = self.tokens[position]
        if self.tokens[position].text == "return":
            node, position = self.expr(position + 1)
            if self.tokens[position].text != ";":
                raise CompileError(self.tokens[position], "expected ';'")
            return Node("RETURN", lhs=node, tok=token), position + 1
        if self.tokens[position].text == "if":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position], "expected '('")
            cond, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            then, position = self.stmt(position + 1)
            els = None
            if self.tokens[position].text == "else":
                els, position = self.stmt(position + 1)
            return Node("IF", cond=cond, then=then, els=els, tok=token), position
        if self.tokens[position].text == "for":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position], "expected '('")
            init, position = self.expr_stmt(position + 1)
            cond = None
            if self.tokens[position].text != ";":
                cond, position = self.expr(position)
            if self.tokens[position].text != ";":
                raise CompileError(self.tokens[position], "expected ';'")
            position += 1
            inc = None
            if self.tokens[position].text != ")":
                inc, position = self.expr(position)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            then, position = self.stmt(position + 1)
            return Node("FOR", init=init, cond=cond, inc=inc, then=then, tok=token), position
        if self.tokens[position].text == "while":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position], "expected '('")
            cond, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            then, position = self.stmt(position + 1)
            return Node("FOR", cond=cond, then=then, tok=token), position
        if self.tokens[position].text == "{":
            return self.compound_stmt(position + 1)
        return self.expr_stmt(position)

    # declspec = "char" | "int" | "struct" struct-decl
    def declspec(self, position):
        if self.tokens[position].text == "char":
            return ty_char, position + 1
        if self.tokens[position].text == "short":
            return ty_short, position + 1
        if self.tokens[position].text == "int":
            return ty_int, position + 1
        if self.tokens[position].text == "long":
            return ty_long, position + 1
        if self.tokens[position].text == "struct":
            return self.struct_decl(position + 1)
        if self.tokens[position].text == "union":
            return self.union_decl(position + 1)
        raise CompileError(self.tokens[position], "typename expected")

    # struct-union-decl = identifier? "{" struct-members "}" | identifier
    def struct_union_decl(self, position):
        tag = None
        if self.tokens[position].kind == "IDENT":
            tag = self.tokens[position]
            position += 1
        if tag is not None and self.tokens[position].text != "{":
            ty = self.find_tag(tag.text)
            if ty is None:
                raise CompileError(tag, "unknown struct type")
            return ty, position
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        position += 1
        members = []
        while self.tokens[position].text != "}":
            basety, position = self.declspec(position)
            first = True
            while self.tokens[position].text != ";":
                if not first:
                    if self.tokens[position].text != ",":
                        raise CompileError(self.tokens[position], "expected ','")
                    position += 1
                first = False
                ty, position = self.declarator(position, basety)
                members.append(Member(ty, ty.name))
            position += 1
        ty = Type("STRUCT", align=1, members=members)
        if tag is not None:
            self.scopes[-1].tags[tag.text] = ty
        return ty, position + 1

    def struct_decl(self, position):
        ty, position = self.struct_union_decl(position)
        ty.kind = "STRUCT"
        offset = 0
        for member in ty.members:
            offset = align_to(offset, member.ty.align)
            member.offset = offset
            offset += member.ty.size
            ty.align = max(ty.align, member.ty.align)
        ty.size = align_to(offset, ty.align)
        return ty, position

    def union_decl(self, position):
        ty, position = self.struct_union_decl(position)
        ty.kind = "UNION"
        for member in ty.members:
            ty.align = max(ty.align, member.ty.align)
            ty.size = max(ty.size, member.ty.size)
        ty.size = align_to(ty.size, ty.align)
        return ty, position

    # func-params = (declspec declarator ("," declspec declarator)*)? ")"
    def func_params(self, position, ty):
        params = []
        while self.tokens[position].text != ")":
            if params:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            basety, position = self.declspec(position)
            param, position = self.declarator(position, basety)
            params.append(copy_type(param))
        ty = func_type(ty)
        ty.params = params
        return ty, position + 1

    # type-suffix = "(" func-params | "[" number "]" type-suffix | empty
    def type_suffix(self, position, ty):
        if self.tokens[position].text == "(":
            return self.func_params(position + 1, ty)
        if self.tokens[position].text == "[":
            token = self.tokens[position + 1]
            if token.kind != "NUM":
                raise CompileError(token, "expected a number")
            if self.tokens[position + 2].text != "]":
                raise CompileError(self.tokens[position + 2], "expected ']'")
            ty, position = self.type_suffix(position + 3, ty)
            return array_of(ty, token.value), position
        return ty, position

    # declarator = "*"* identifier type-suffix
    def declarator(self, position, ty):
        while self.tokens[position].text == "*":
            ty = pointer_to(ty)
            position += 1
        token = self.tokens[position]
        if token.kind != "IDENT":
            raise CompileError(token, "expected a variable name")
        # Keep the declaration name without mutating the shared integer type.
        ty, position = self.type_suffix(position + 1, ty)
        ty = copy_type(ty)
        ty.name = token
        return ty, position

    # declaration = declspec (declarator ("=" assign)?
    #                        ("," declarator ("=" assign)?)*)? ";"
    def declaration(self, position):
        basety, position = self.declspec(position)
        statements = []
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            var = self.new_lvar(ty.name.text, ty)
            if self.tokens[position].text != "=":
                continue
            lhs = Node("VAR", var=var, tok=ty.name)
            rhs, position = self.assign(position + 1)
            token = self.tokens[position]
            assignment = Node("ASSIGN", lhs, rhs, tok=token)
            statements.append(Node("EXPR_STMT", lhs=assignment, tok=token))
        return Node("BLOCK", body=statements, tok=self.tokens[position]), position + 1

    # compound-stmt = (declaration | stmt)* "}"
    def compound_stmt(self, position):
        token = self.tokens[position]
        statements = []
        self.enter_scope()
        while self.tokens[position].text != "}":
            if self.tokens[position].text in ("char", "short", "int", "long", "struct", "union"):
                node, position = self.declaration(position)
            else:
                node, position = self.stmt(position)
            add_type(node)
            statements.append(node)
        self.leave_scope()
        return Node("BLOCK", body=statements, tok=token), position + 1

    # expr-stmt = expr? ";"
    def expr_stmt(self, position):
        token = self.tokens[position]
        if self.tokens[position].text == ";":
            return Node("BLOCK", tok=token), position + 1
        node, position = self.expr(position)
        if self.tokens[position].text != ";":
            raise CompileError(self.tokens[position], "expected ';'")
        return Node("EXPR_STMT", lhs=node, tok=token), position + 1

    def function(self, position, basety):
        ty, position = self.declarator(position, basety)
        function = self.new_gvar(ty.name.text, ty)
        function.is_function = True
        self.locals = []
        self.enter_scope()
        for param in reversed(ty.params):
            self.new_lvar(param.name.text, param)
        function.params = self.locals.copy()
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        function.body, position = self.compound_stmt(position + 1)
        function.locals = self.locals
        self.leave_scope()
        return position

    def global_variable(self, position, basety):
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            self.new_gvar(ty.name.text, ty)
        return position + 1

    def is_function(self, position):
        if self.tokens[position].text == ";":
            return False
        ty, _ = self.declarator(position, Type("INT"))
        return ty.kind == "FUNC"

    # program = (function-definition | global-variable)*
    def parse(self):
        position = 0
        while self.tokens[position].kind != "EOF":
            basety, position = self.declspec(position)
            if self.is_function(position):
                position = self.function(position, basety)
            else:
                position = self.global_variable(position, basety)
        return self.globals


def parse(tokens):
    return Parser(tokens).parse()
