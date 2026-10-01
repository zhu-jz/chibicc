"""Build a function using recursive descent.

Each grammar function returns a node and the next token index. Python tuples
replace C's returned node plus output pointer for the remaining tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from common import CompileError, Member, Node, Obj, Scope, Type, VarAttr, VarScope, align_to
from type import add_type, array_of, copy_type, enum_type, func_type, is_integer, new_cast, pointer_to, struct_type, ty_void, ty_bool, ty_char, ty_short, ty_int, ty_long


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
    rhs = Node("*", rhs, Node("NUM", value=lhs.ty.base.size, tok=token, ty=ty_long), tok=token)
    return Node("+", lhs, rhs, tok=token)


def new_sub(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_integer(lhs.ty) and is_integer(rhs.ty):
        return Node("-", lhs, rhs, tok=token)
    if lhs.ty.base is not None and is_integer(rhs.ty):
        rhs = Node("*", rhs, Node("NUM", value=lhs.ty.base.size, tok=token, ty=ty_long), tok=token)
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
        self.current_fn = None
        self.gotos = []
        self.labels = []
        self.brk_label = None
        self.cont_label = None

    def enter_scope(self):
        self.scopes.append(Scope())

    def new_unique_name(self):
        name = f".L..{self.unique_id}"
        self.unique_id += 1
        return name

    def leave_scope(self):
        self.scopes.pop()

    def push_scope(self, name):
        binding = VarScope(name)
        self.scopes[-1].vars.insert(0, binding)
        return binding

    def new_lvar(self, name, ty):
        var = Obj(name, ty=ty, is_local=True)
        self.locals.insert(0, var)
        self.push_scope(name).var = var
        return var

    def new_gvar(self, name, ty):
        var = Obj(name, ty=ty)
        self.globals.insert(0, var)
        self.push_scope(name).var = var
        return var

    def new_string_literal(self, data, ty):
        var = self.new_gvar(f".L..{self.unique_id}", ty)
        self.unique_id += 1
        var.init_data = data
        return var

    def find_var(self, name):
        for scope in reversed(self.scopes):
            for binding in scope.vars:
                if binding.name == name:
                    return binding
        return None

    def find_tag(self, name):
        for scope in reversed(self.scopes):
            if name in scope.tags:
                return scope.tags[name]
        return None

    def find_typedef(self, position):
        token = self.tokens[position]
        if token.kind == "IDENT":
            binding = self.find_var(token.text)
            if binding is not None:
                return binding.type_def
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

    def to_assign(self, binary):
        """Lower A op= B while evaluating A's address exactly once."""
        add_type(binary.lhs)
        add_type(binary.rhs)
        token = binary.tok
        temporary = self.new_lvar("", pointer_to(binary.lhs.ty))
        save_address = Node("ASSIGN", Node("VAR", var=temporary, tok=token),
                            Node("ADDR", lhs=binary.lhs, tok=token), tok=token)
        target = Node("DEREF", lhs=Node("VAR", var=temporary, tok=token), tok=token)
        value = Node("DEREF", lhs=Node("VAR", var=temporary, tok=token), tok=token)
        operation = Node(binary.kind, value, binary.rhs, tok=token)
        update = Node("ASSIGN", target, operation, tok=token)
        return Node("COMMA", save_address, update, tok=token)

    # assign = logor (assign-op assign)?
    def assign(self, position):
        node, position = self.logor(position)
        if self.tokens[position].text == "=":
            token = self.tokens[position]
            rhs, position = self.assign(position + 1)
            node = Node("ASSIGN", node, rhs, tok=token)
        elif self.tokens[position].text in ("+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="):
            token = self.tokens[position]
            rhs, position = self.assign(position + 1)
            if token.text == "+=":
                binary = new_add(node, rhs, token)
            elif token.text == "-=":
                binary = new_sub(node, rhs, token)
            else:
                binary = Node(token.text[0], node, rhs, tok=token)
            node = self.to_assign(binary)
        return node, position

    # logor = logand ("||" logand)*
    def logor(self, position):
        node, position = self.logand(position)
        while self.tokens[position].text == "||":
            token = self.tokens[position]
            rhs, position = self.logand(position + 1)
            node = Node("LOGOR", node, rhs, tok=token)
        return node, position

    # logand = bitor ("&&" bitor)*
    def logand(self, position):
        node, position = self.bitor(position)
        while self.tokens[position].text == "&&":
            token = self.tokens[position]
            rhs, position = self.bitor(position + 1)
            node = Node("LOGAND", node, rhs, tok=token)
        return node, position

    # bitor = bitxor ("|" bitxor)*
    def bitor(self, position):
        node, position = self.bitxor(position)
        while self.tokens[position].text == "|":
            token = self.tokens[position]
            rhs, position = self.bitxor(position + 1)
            node = Node("|", node, rhs, tok=token)
        return node, position

    # bitxor = bitand ("^" bitand)*
    def bitxor(self, position):
        node, position = self.bitand(position)
        while self.tokens[position].text == "^":
            token = self.tokens[position]
            rhs, position = self.bitand(position + 1)
            node = Node("^", node, rhs, tok=token)
        return node, position

    # bitand = equality ("&" equality)*
    def bitand(self, position):
        node, position = self.equality(position)
        while self.tokens[position].text == "&":
            token = self.tokens[position]
            rhs, position = self.equality(position + 1)
            node = Node("&", node, rhs, tok=token)
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

    # mul = cast (("*" | "/") cast)*
    def mul(self, position):
        node, position = self.cast(position)
        while self.tokens[position].text in ("*", "/", "%"):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.cast(position + 1)
            node = Node(operator, node, rhs, tok=token)
        return node, position

    # cast = "(" type-name ")" cast | unary
    def cast(self, position):
        token = self.tokens[position]
        if token.text == "(" and self.is_typename(position + 1):
            ty, position = self.typename(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            operand, position = self.cast(position + 1)
            node = new_cast(operand, ty)
            node.tok = token
            return node, position
        return self.unary(position)

    # unary = ("+" | "-" | "*" | "&") cast | postfix
    def unary(self, position):
        token = self.tokens[position]
        operator = self.tokens[position].text
        if operator == "+":
            return self.cast(position + 1)
        if operator == "-":
            operand, position = self.cast(position + 1)
            return Node("NEG", lhs=operand, tok=token), position
        if operator == "&":
            operand, position = self.cast(position + 1)
            return Node("ADDR", lhs=operand, tok=token), position
        if operator == "*":
            operand, position = self.cast(position + 1)
            return Node("DEREF", lhs=operand, tok=token), position
        if operator == "!":
            operand, position = self.cast(position + 1)
            return Node("NOT", lhs=operand, tok=token), position
        if operator == "~":
            operand, position = self.cast(position + 1)
            return Node("BITNOT", lhs=operand, tok=token), position
        if operator in ("++", "--"):
            operand, position = self.unary(position + 1)
            one = Node("NUM", value=1, tok=token)
            binary = new_add(operand, one, token) if operator == "++" else new_sub(operand, one, token)
            return self.to_assign(binary), position
        return self.postfix(position)

    def struct_ref(self, lhs, token):
        add_type(lhs)
        if lhs.ty.kind not in ("STRUCT", "UNION"):
            raise CompileError(lhs.tok, "not a struct nor a union")
        for member in lhs.ty.members:
            if member.name.text == token.text:
                return Node("MEMBER", lhs=lhs, member=member, tok=token)
        raise CompileError(token, "no such member")

    def new_inc_dec(self, node, token, addend):
        add_type(node)
        update = self.to_assign(new_add(node, Node("NUM", value=addend, tok=token), token))
        old_value = new_add(update, Node("NUM", value=-addend, tok=token), token)
        return new_cast(old_value, node.ty)

    # postfix = primary ("[" expr "]" | "." identifier | "->" identifier | "++" | "--")*
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
            elif self.tokens[position].text in ("++", "--"):
                token = self.tokens[position]
                node = self.new_inc_dec(node, token, 1 if token.text == "++" else -1)
                position += 1
            else:
                return node, position

    # funcall = identifier "(" (assign ("," assign)*)? ")"
    def funcall(self, position):
        token = self.tokens[position]
        binding = self.find_var(token.text)
        if binding is None:
            raise CompileError(token, "implicit declaration of a function")
        if binding.var is None or binding.var.ty.kind != "FUNC":
            raise CompileError(token, "not a function")
        function_ty = binding.var.ty
        position += 2
        args = []
        while self.tokens[position].text != ")":
            if args:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            arg, position = self.assign(position)
            add_type(arg)
            if len(args) < len(function_ty.params):
                param_ty = function_ty.params[len(args)]
                if param_ty.kind in ("STRUCT", "UNION"):
                    raise CompileError(arg.tok, "passing struct or union is not supported yet")
                arg = new_cast(arg, param_ty)
            args.append(arg)
        return Node("FUNCALL", funcname=token.text, args=args, tok=token,
                    ty=function_ty.return_ty, func_ty=function_ty), position + 1

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

        if (token.text == "sizeof" and self.tokens[position + 1].text == "("
                and self.is_typename(position + 2)):
            ty, position = self.typename(position + 2)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            return Node("NUM", value=ty.size, tok=token), position + 1

        if token.text == "sizeof":
            operand, position = self.unary(position + 1)
            add_type(operand)
            return Node("NUM", value=operand.ty.size, tok=token), position

        if token.kind == "IDENT":
            if self.tokens[position + 1].text == "(":
                return self.funcall(position)
            binding = self.find_var(token.text)
            if binding is None or (binding.var is None and binding.enum_ty is None):
                raise CompileError(token, "undefined variable")
            if binding.var is None:
                return Node("NUM", value=binding.enum_val, tok=token), position + 1
            return Node("VAR", var=binding.var, tok=token), position + 1

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
            node = new_cast(node, self.current_fn.ty.return_ty)
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
            self.enter_scope()
            previous_break = self.brk_label
            previous_continue = self.cont_label
            self.brk_label = break_label = self.new_unique_name()
            self.cont_label = continue_label = self.new_unique_name()
            position += 1
            if self.is_typename(position):
                basety, position = self.declspec(position)
                init, position = self.declaration(position, basety)
            else:
                init, position = self.expr_stmt(position)
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
            self.leave_scope()
            self.brk_label = previous_break
            self.cont_label = previous_continue
            return Node("FOR", init=init, cond=cond, inc=inc, then=then, tok=token,
                        brk_label=break_label, cont_label=continue_label), position
        if self.tokens[position].text == "while":
            position += 1
            if self.tokens[position].text != "(":
                raise CompileError(self.tokens[position], "expected '('")
            cond, position = self.expr(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            previous_break = self.brk_label
            previous_continue = self.cont_label
            self.brk_label = break_label = self.new_unique_name()
            self.cont_label = continue_label = self.new_unique_name()
            then, position = self.stmt(position + 1)
            self.brk_label = previous_break
            self.cont_label = previous_continue
            return Node("FOR", cond=cond, then=then, tok=token, brk_label=break_label,
                        cont_label=continue_label), position
        if self.tokens[position].text == "{":
            return self.compound_stmt(position + 1)
        if token.text == "goto":
            name = self.tokens[position + 1]
            if name.kind != "IDENT":
                raise CompileError(name, "expected a variable name")
            if self.tokens[position + 2].text != ";":
                raise CompileError(self.tokens[position + 2], "expected ';'")
            node = Node("GOTO", label=name.text, tok=token)
            self.gotos.insert(0, (node, name))
            return node, position + 3
        if token.kind == "IDENT" and self.tokens[position + 1].text == ":":
            unique = f".L..{self.unique_id}"
            self.unique_id += 1
            statement, position = self.stmt(position + 2)
            node = Node("LABEL", lhs=statement, label=token.text, unique_label=unique, tok=token)
            self.labels.insert(0, node)
            return node, position
        if token.text == "break":
            if self.brk_label is None:
                raise CompileError(token, "stray break")
            if self.tokens[position + 1].text != ";":
                raise CompileError(self.tokens[position + 1], "expected ';'")
            return Node("GOTO", unique_label=self.brk_label, tok=token), position + 2
        if token.text == "continue":
            if self.cont_label is None:
                raise CompileError(token, "stray continue")
            if self.tokens[position + 1].text != ";":
                raise CompileError(self.tokens[position + 1], "expected ';'")
            return Node("GOTO", unique_label=self.cont_label, tok=token), position + 2
        return self.expr_stmt(position)

    def is_typename(self, position):
        return self.tokens[position].text in ("void", "_Bool", "char", "short", "int", "long",
                                              "struct", "union", "typedef", "enum", "static") or self.find_typedef(position) is not None

    # declspec = ("void" | "char" | "short" | "int" | "long"
    #             | struct-decl | union-decl)*
    def declspec(self, position, attr=None):
        combinations = {
            ("void",): ty_void,
            ("_Bool",): ty_bool, ("char",): ty_char,
            ("short",): ty_short, ("int", "short"): ty_short,
            ("int",): ty_int,
            ("long",): ty_long, ("int", "long"): ty_long,
            ("long", "long"): ty_long, ("int", "long", "long"): ty_long,
        }
        ty = ty_int
        specifiers = []
        while self.is_typename(position):
            token = self.tokens[position]
            if token.text in ("typedef", "static"):
                if attr is None:
                    raise CompileError(token, "storage class specifier is not allowed in this context")
                if token.text == "typedef":
                    attr.is_typedef = True
                else:
                    attr.is_static = True
                if attr.is_typedef and attr.is_static:
                    raise CompileError(token, "typedef and static may not be used together")
                position += 1
                continue
            type_def = self.find_typedef(position)
            if token.text in ("struct", "union", "enum") or type_def is not None:
                if specifiers:
                    break
                if token.text == "struct":
                    ty, position = self.struct_decl(position + 1)
                elif token.text == "union":
                    ty, position = self.union_decl(position + 1)
                elif token.text == "enum":
                    ty, position = self.enum_specifier(position + 1)
                else:
                    ty = type_def
                    position += 1
                specifiers.append("other")
                continue
            specifiers.append(token.text)
            ty = combinations.get(tuple(sorted(specifiers)))
            if ty is None:
                raise CompileError(token, "invalid type")
            position += 1
        return ty, position

    # struct-union-decl = identifier? "{" struct-members "}" | identifier
    def struct_union_decl(self, position):
        tag = None
        if self.tokens[position].kind == "IDENT":
            tag = self.tokens[position]
            position += 1
        if tag is not None and self.tokens[position].text != "{":
            ty = self.find_tag(tag.text)
            if ty is None:
                ty = struct_type()
                ty.size = -1
                self.scopes[-1].tags[tag.text] = ty
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
        ty = struct_type()
        ty.members = members
        if tag is not None:
            previous = self.scopes[-1].tags.get(tag.text)
            if previous is not None:
                # Preserve references held by earlier pointers and typedefs.
                previous.__dict__.update(ty.__dict__)
                return previous, position + 1
            self.scopes[-1].tags[tag.text] = ty
        return ty, position + 1

    def struct_decl(self, position):
        ty, position = self.struct_union_decl(position)
        ty.kind = "STRUCT"
        if ty.size < 0:
            return ty, position
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
        if ty.size < 0:
            return ty, position
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
            if param.kind == "ARRAY":
                name = param.name
                param = pointer_to(param.base)
                param.name = name
            params.append(copy_type(param))
        ty = func_type(ty)
        ty.params = params
        return ty, position + 1

    def array_dimensions(self, position, ty):
        if self.tokens[position].text == "]":
            ty, position = self.type_suffix(position + 1, ty)
            return array_of(ty, -1), position
        token = self.tokens[position]
        if token.kind != "NUM":
            raise CompileError(token, "expected a number")
        if self.tokens[position + 1].text != "]":
            raise CompileError(self.tokens[position + 1], "expected ']'")
        ty, position = self.type_suffix(position + 2, ty)
        return array_of(ty, token.value), position

    # type-suffix = "(" func-params | "[" array-dimensions | empty
    def type_suffix(self, position, ty):
        if self.tokens[position].text == "(":
            return self.func_params(position + 1, ty)
        if self.tokens[position].text == "[":
            return self.array_dimensions(position + 1, ty)
        return ty, position

    # declarator = "*"* (identifier | "(" declarator ")") type-suffix
    def declarator(self, position, ty):
        while self.tokens[position].text == "*":
            ty = pointer_to(ty)
            position += 1
        if self.tokens[position].text == "(":
            start = position + 1
            _, end = self.declarator(start, Type("DUMMY"))
            if self.tokens[end].text != ")":
                raise CompileError(self.tokens[end], "expected ')'")
            ty, position = self.type_suffix(end + 1, ty)
            ty, _ = self.declarator(start, ty)
            return ty, position
        token = self.tokens[position]
        if token.kind != "IDENT":
            raise CompileError(token, "expected a variable name")
        # Keep the declaration name without mutating the shared integer type.
        ty, position = self.type_suffix(position + 1, ty)
        if ty.kind not in ("STRUCT", "UNION"):
            ty = copy_type(ty)
        ty.name = token
        return ty, position

    # abstract-declarator = "*"* ("(" abstract-declarator ")")? type-suffix
    def abstract_declarator(self, position, ty):
        while self.tokens[position].text == "*":
            ty = pointer_to(ty)
            position += 1
        if self.tokens[position].text == "(":
            start = position + 1
            _, end = self.abstract_declarator(start, Type("DUMMY"))
            if self.tokens[end].text != ")":
                raise CompileError(self.tokens[end], "expected ')'")
            ty, position = self.type_suffix(end + 1, ty)
            ty, _ = self.abstract_declarator(start, ty)
            return ty, position
        return self.type_suffix(position, ty)

    def typename(self, position):
        ty, position = self.declspec(position)
        return self.abstract_declarator(position, ty)

    def enum_specifier(self, position):
        ty = enum_type()
        tag = None
        if self.tokens[position].kind == "IDENT":
            tag = self.tokens[position]
            position += 1
        if tag is not None and self.tokens[position].text != "{":
            ty = self.find_tag(tag.text)
            if ty is None:
                raise CompileError(tag, "unknown enum type")
            if ty.kind != "ENUM":
                raise CompileError(tag, "not an enum tag")
            return ty, position
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        position += 1
        value = 0
        first = True
        while self.tokens[position].text != "}":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            token = self.tokens[position]
            if token.kind != "IDENT":
                raise CompileError(token, "expected a variable name")
            position += 1
            if self.tokens[position].text == "=":
                number = self.tokens[position + 1]
                if number.kind != "NUM":
                    raise CompileError(number, "expected a number")
                value = number.value
                position += 2
            binding = self.push_scope(token.text)
            binding.enum_ty = ty
            binding.enum_val = value
            value += 1
        if tag is not None:
            self.scopes[-1].tags[tag.text] = ty
        return ty, position + 1

    # declaration = declspec (declarator ("=" assign)?
    #                        ("," declarator ("=" assign)?)*)? ";"
    def declaration(self, position, basety):
        statements = []
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            if ty.size < 0:
                raise CompileError(self.tokens[position], "variable has incomplete type")
            if ty.kind == "VOID":
                raise CompileError(self.tokens[position], "variable declared void")
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
            if self.is_typename(position) and self.tokens[position + 1].text != ":":
                attr = VarAttr()
                basety, position = self.declspec(position, attr)
                if attr.is_typedef:
                    position = self.parse_typedef(position, basety)
                    continue
                node, position = self.declaration(position, basety)
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

    def resolve_goto_labels(self):
        for jump, token in self.gotos:
            for label in self.labels:
                if jump.label == label.label:
                    jump.unique_label = label.unique_label
                    break
            if jump.unique_label is None:
                raise CompileError(token, "use of undeclared label")
        self.gotos = []
        self.labels = []

    def function(self, position, basety, attr):
        ty, position = self.declarator(position, basety)
        function = self.new_gvar(ty.name.text, ty)
        function.is_function = True
        function.is_static = attr.is_static
        if self.tokens[position].text == ";":
            return position + 1
        function.is_definition = True
        self.current_fn = function
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
        self.resolve_goto_labels()
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

    def parse_typedef(self, position, basety):
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            self.push_scope(ty.name.text).type_def = ty
        return position + 1

    # program = (typedef | function-definition | global-variable)*
    def parse(self):
        position = 0
        while self.tokens[position].kind != "EOF":
            attr = VarAttr()
            basety, position = self.declspec(position, attr)
            if attr.is_typedef:
                position = self.parse_typedef(position, basety)
                continue
            if self.is_function(position):
                position = self.function(position, basety, attr)
            else:
                position = self.global_variable(position, basety)
        return self.globals


def parse(tokens):
    return Parser(tokens).parse()
