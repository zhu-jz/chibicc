"""Build a function using recursive descent.

Each grammar function returns a node and the next token index. Python tuples
replace C's returned node plus output pointer for the remaining tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from dataclasses import replace

from common import CompileError, Member, Node, Obj, Scope, Type, VarAttr, VarScope, align_to
from common import Initializer, InitDesg, Relocation, to_int32
from constexpr import evaluate_constant, evaluate_initializer
from type import ty_uchar, ty_ushort, ty_uint, ty_ulong, ty_float, ty_double
from type import is_numeric
from type import add_type, array_of, copy_type, enum_type, func_type, is_integer, new_cast, pointer_to, struct_type, ty_void, ty_bool, ty_char, ty_short, ty_int, ty_long


def new_add(lhs, rhs, token):
    add_type(lhs)
    add_type(rhs)
    if is_numeric(lhs.ty) and is_numeric(rhs.ty):
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
    if is_numeric(lhs.ty) and is_numeric(rhs.ty):
        return Node("-", lhs, rhs, tok=token)
    if lhs.ty.base is not None and is_integer(rhs.ty):
        rhs = Node("*", rhs, Node("NUM", value=lhs.ty.base.size, tok=token, ty=ty_long), tok=token)
        add_type(rhs)
        return Node("-", lhs, rhs, tok=token, ty=lhs.ty)
    if lhs.ty.base is not None and rhs.ty.base is not None:
        difference = Node("-", lhs, rhs, tok=token, ty=ty_long)
        return Node("/", difference, Node("NUM", value=lhs.ty.base.size, tok=token), tok=token)
    raise CompileError(token, "invalid operands")


def new_initializer(ty, is_flexible=False):
    init = Initializer(ty)
    if ty.kind == "ARRAY":
        if is_flexible and ty.size < 0:
            init.is_flexible = True
            return init
        init.children = [new_initializer(ty.base) for _ in range(ty.array_len)]
    elif ty.kind in ("STRUCT", "UNION"):
        for index, member in enumerate(ty.members):
            if is_flexible and ty.is_flexible and index == len(ty.members) - 1:
                init.children.append(Initializer(member.ty, is_flexible=True))
            else:
                init.children.append(new_initializer(member.ty))
    return init


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
        self.current_switch = None

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
        var = Obj(name, ty=ty, is_local=True, align=ty.align)
        self.locals.insert(0, var)
        self.push_scope(name).var = var
        return var

    def new_gvar(self, name, ty):
        var = Obj(name, ty=ty, is_definition=True, is_static=True, align=ty.align)
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

    def const_expr(self, position):
        node, position = self.conditional(position)
        return evaluate_constant(node), position

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

    # assign = conditional (assign-op assign)?
    def assign(self, position):
        node, position = self.conditional(position)
        if self.tokens[position].text == "=":
            token = self.tokens[position]
            rhs, position = self.assign(position + 1)
            node = Node("ASSIGN", node, rhs, tok=token)
        elif self.tokens[position].text in ("+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="):
            token = self.tokens[position]
            rhs, position = self.assign(position + 1)
            if token.text == "+=":
                binary = new_add(node, rhs, token)
            elif token.text == "-=":
                binary = new_sub(node, rhs, token)
            else:
                binary = Node(token.text[:-1], node, rhs, tok=token)
            node = self.to_assign(binary)
        return node, position

    # conditional = logor ("?" expr ":" conditional)?
    def conditional(self, position):
        cond, position = self.logor(position)
        if self.tokens[position].text != "?":
            return cond, position
        token = self.tokens[position]
        then, position = self.expr(position + 1)
        if self.tokens[position].text != ":":
            raise CompileError(self.tokens[position], "expected ':'")
        otherwise, position = self.conditional(position + 1)
        return Node("COND", cond=cond, then=then, els=otherwise, tok=token), position

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

    # relational = shift (("<" | "<=" | ">" | ">=") shift)*
    def relational(self, position):
        node, position = self.shift(position)
        while self.tokens[position].text in ("<", "<=", ">", ">="):
            token = self.tokens[position]
            operator = self.tokens[position].text
            rhs, position = self.shift(position + 1)
            if operator == ">":
                node = Node("<", rhs, node, tok=token)
            elif operator == ">=":
                node = Node("<=", rhs, node, tok=token)
            else:
                node = Node(operator, node, rhs, tok=token)
        return node, position

    # shift = add (("<<" | ">>") add)*
    def shift(self, position):
        node, position = self.add(position)
        while self.tokens[position].text in ("<<", ">>"):
            token = self.tokens[position]
            rhs, position = self.add(position + 1)
            node = Node(token.text, node, rhs, tok=token)
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
            start = position
            ty, position = self.typename(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            if self.tokens[position + 1].text == "{":
                return self.unary(start)
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
        if self.tokens[position].text == "(" and self.is_typename(position + 1):
            start = self.tokens[position]
            ty, position = self.typename(position + 1)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            position += 1
            if len(self.scopes) == 1:
                var = self.new_gvar(self.new_unique_name(), ty)
                position = self.gvar_initializer(position, var)
                return Node("VAR", var=var, tok=start), position
            var = self.new_lvar("", ty)
            initialization, position = self.lvar_initializer(position, var)
            value = Node("VAR", var=var, tok=self.tokens[position])
            return Node("COMMA", initialization, value, tok=start), position
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
            if len(args) >= len(function_ty.params) and not function_ty.is_variadic:
                raise CompileError(self.tokens[position], "too many arguments")
            if len(args) < len(function_ty.params):
                param_ty = function_ty.params[len(args)]
                if param_ty.kind in ("STRUCT", "UNION"):
                    raise CompileError(arg.tok, "passing struct or union is not supported yet")
                arg = new_cast(arg, param_ty)
            args.append(arg)
        if len(args) < len(function_ty.params):
            raise CompileError(self.tokens[position], "too few arguments")
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
            return Node("NUM", value=ty.size, tok=token, ty=ty_ulong), position + 1

        if token.text == "sizeof":
            operand, position = self.unary(position + 1)
            add_type(operand)
            return Node("NUM", value=operand.ty.size, tok=token, ty=ty_ulong), position

        if (token.text == "_Alignof" and self.tokens[position + 1].text == "("
                and self.is_typename(position + 2)):
            ty, position = self.typename(position + 2)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            return Node("NUM", value=ty.align, tok=token, ty=ty_ulong), position + 1

        if token.text == "_Alignof":
            operand, position = self.unary(position + 1)
            add_type(operand)
            return Node("NUM", value=operand.ty.align, tok=token, ty=ty_ulong), position

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
            return Node("NUM", value=token.value, tok=token, ty=token.ty,
                        fvalue=token.fvalue), position + 1

        raise CompileError(token, "expected an expression")

    # stmt = "return" expr ";" | "{" compound-stmt | expr-stmt
    #      | "if" "(" expr ")" stmt ("else" stmt)?
    #      | "for" "(" expr-stmt expr? ";" expr? ")" stmt
    #      | "while" "(" expr ")" stmt
    def stmt(self, position):
        token = self.tokens[position]
        if self.tokens[position].text == "return":
            if self.tokens[position + 1].text == ";":
                return Node("RETURN", tok=token), position + 2
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
        if token.text == "switch":
            if self.tokens[position + 1].text != "(":
                raise CompileError(self.tokens[position + 1], "expected '('")
            cond, position = self.expr(position + 2)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            node = Node("SWITCH", cond=cond, tok=token, brk_label=self.new_unique_name())
            previous_switch = self.current_switch
            previous_break = self.brk_label
            self.current_switch = node
            self.brk_label = node.brk_label
            node.then, position = self.stmt(position + 1)
            self.current_switch = previous_switch
            self.brk_label = previous_break
            return node, position
        if token.text in ("case", "default"):
            if self.current_switch is None:
                raise CompileError(token, "stray " + token.text)
            value = 0
            position += 1
            if token.text == "case":
                value, position = self.const_expr(position)
                value = to_int32(value)
            if self.tokens[position].text != ":":
                raise CompileError(self.tokens[position], "expected ':'")
            node = Node("CASE", value=value, label=self.new_unique_name(), tok=token)
            node.lhs, position = self.stmt(position + 1)
            if token.text == "case":
                self.current_switch.cases.insert(0, node)
            else:
                self.current_switch.default_case = node
            return node, position
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
        if token.text == "do":
            previous_break, previous_continue = self.brk_label, self.cont_label
            self.brk_label = break_label = self.new_unique_name()
            self.cont_label = continue_label = self.new_unique_name()
            body, position = self.stmt(position + 1)
            self.brk_label, self.cont_label = previous_break, previous_continue
            if self.tokens[position].text != "while":
                raise CompileError(self.tokens[position], "expected 'while'")
            if self.tokens[position + 1].text != "(":
                raise CompileError(self.tokens[position + 1], "expected '('")
            condition, position = self.expr(position + 2)
            if self.tokens[position].text != ")":
                raise CompileError(self.tokens[position], "expected ')'")
            if self.tokens[position + 1].text != ";":
                raise CompileError(self.tokens[position + 1], "expected ';'")
            return Node("DO", then=body, cond=condition, tok=token,
                        brk_label=break_label, cont_label=continue_label), position + 2
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
                                              "struct", "union", "typedef", "enum", "static", "extern", "_Alignas", "signed", "unsigned",
                                              "const", "volatile", "auto", "register", "restrict", "__restrict", "__restrict__", "_Noreturn", "float", "double") or self.find_typedef(position) is not None

    # declspec = ("void" | "char" | "short" | "int" | "long"
    #             | struct-decl | union-decl)*
    def declspec(self, position, attr=None):
        combinations = {
            ("float",): ty_float, ("double",): ty_double,
            ("void",): ty_void,
            ("_Bool",): ty_bool, ("char",): ty_char,
            ("short",): ty_short, ("int", "short"): ty_short,
            ("int",): ty_int,
            ("long",): ty_long, ("int", "long"): ty_long,
            ("long", "long"): ty_long, ("int", "long", "long"): ty_long,
        }
        ty = ty_int
        specifiers = []
        has_signed = False
        has_unsigned = False
        unsigned_types = {"CHAR": ty_uchar, "SHORT": ty_ushort, "INT": ty_uint, "LONG": ty_ulong}
        while self.is_typename(position):
            token = self.tokens[position]
            if token.text in ("const", "volatile", "auto", "register", "restrict",
                              "__restrict", "__restrict__", "_Noreturn"):
                position += 1
                continue
            if token.text in ("typedef", "static", "extern"):
                if attr is None:
                    raise CompileError(token, "storage class specifier is not allowed in this context")
                if token.text == "typedef":
                    attr.is_typedef = True
                elif token.text == "static":
                    attr.is_static = True
                else:
                    attr.is_extern = True
                if attr.is_typedef and attr.is_static + attr.is_extern > 1:
                    raise CompileError(token, "typedef may not be used together with static or extern")
                position += 1
                continue
            if token.text == "_Alignas":
                if attr is None:
                    raise CompileError(token, "_Alignas is not allowed in this context")
                if self.tokens[position + 1].text != "(":
                    raise CompileError(self.tokens[position + 1], "expected '('")
                position += 2
                if self.is_typename(position):
                    alignment_ty, position = self.typename(position)
                    attr.align = alignment_ty.align
                else:
                    attr.align, position = self.const_expr(position)
                    attr.align = to_int32(attr.align)
                if self.tokens[position].text != ")":
                    raise CompileError(self.tokens[position], "expected ')'")
                position += 1
                continue
            if token.text in ("signed", "unsigned"):
                if token.text == "signed":
                    has_signed = True
                else:
                    has_unsigned = True
                if has_signed and has_unsigned:
                    raise CompileError(token, "invalid type")
                if "other" in specifiers or ty.kind not in ("CHAR", "SHORT", "INT", "LONG"):
                    raise CompileError(token, "invalid type")
                if has_unsigned:
                    ty = unsigned_types[ty.kind]
                position += 1
                continue
            type_def = self.find_typedef(position)
            if token.text in ("struct", "union", "enum") or type_def is not None:
                if specifiers or has_signed or has_unsigned:
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
            if (has_signed or has_unsigned) and ty.kind not in ("CHAR", "SHORT", "INT", "LONG"):
                raise CompileError(token, "invalid type")
            if has_unsigned:
                ty = unsigned_types[ty.kind]
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
            attr = VarAttr()
            basety, position = self.declspec(position, attr)
            first = True
            while self.tokens[position].text != ";":
                if not first:
                    if self.tokens[position].text != ",":
                        raise CompileError(self.tokens[position], "expected ','")
                    position += 1
                first = False
                ty, position = self.declarator(position, basety)
                members.append(Member(ty, ty.name, idx=len(members), align=attr.align or ty.align))
            position += 1
        ty = struct_type()
        if members and members[-1].ty.kind == "ARRAY" and members[-1].ty.array_len < 0:
            members[-1].ty = array_of(members[-1].ty.base, 0)
            ty.is_flexible = True
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
            offset = align_to(offset, member.align)
            member.offset = offset
            offset += member.ty.size
            ty.align = max(ty.align, member.align)
        ty.size = align_to(offset, ty.align)
        return ty, position

    def union_decl(self, position):
        ty, position = self.struct_union_decl(position)
        ty.kind = "UNION"
        if ty.size < 0:
            return ty, position
        for member in ty.members:
            ty.align = max(ty.align, member.align)
            ty.size = max(ty.size, member.ty.size)
        ty.size = align_to(ty.size, ty.align)
        return ty, position

    # func-params = (declspec declarator ("," declspec declarator)*)? ")"
    def func_params(self, position, ty):
        if self.tokens[position].text == "void" and self.tokens[position + 1].text == ")":
            return func_type(ty), position + 2
        params = []
        is_variadic = False
        while self.tokens[position].text != ")":
            if params:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            if self.tokens[position].text == "...":
                is_variadic = True
                position += 1
                if self.tokens[position].text != ")":
                    raise CompileError(self.tokens[position], "expected ')'")
                break
            basety, position = self.declspec(position)
            param, position = self.declarator(position, basety)
            if param.kind == "ARRAY":
                name = param.name
                name_pos = param.name_pos
                param = pointer_to(param.base)
                param.name = name
                param.name_pos = name_pos
            params.append(copy_type(param))
        ty = func_type(ty)
        ty.params = params
        ty.is_variadic = is_variadic or not params
        return ty, position + 1

    def array_dimensions(self, position, ty):
        while self.tokens[position].text in ("static", "restrict"):
            position += 1
        if self.tokens[position].text == "]":
            ty, position = self.type_suffix(position + 1, ty)
            return array_of(ty, -1), position
        length, position = self.const_expr(position)
        if self.tokens[position].text != "]":
            raise CompileError(self.tokens[position], "expected ']'")
        ty, position = self.type_suffix(position + 1, ty)
        return array_of(ty, to_int32(length)), position

    # type-suffix = "(" func-params | "[" array-dimensions | empty
    def type_suffix(self, position, ty):
        if self.tokens[position].text == "(":
            return self.func_params(position + 1, ty)
        if self.tokens[position].text == "[":
            return self.array_dimensions(position + 1, ty)
        return ty, position

    # declarator = "*"* (identifier | "(" declarator ")") type-suffix
    def pointers(self, position, ty):
        while self.tokens[position].text == "*":
            ty = pointer_to(ty)
            position += 1
            while self.tokens[position].text in ("const", "volatile", "restrict", "__restrict", "__restrict__"):
                position += 1
        return ty, position

    def declarator(self, position, ty):
        ty, position = self.pointers(position, ty)
        if self.tokens[position].text == "(":
            start = position + 1
            _, end = self.declarator(start, Type("DUMMY"))
            if self.tokens[end].text != ")":
                raise CompileError(self.tokens[end], "expected ')'")
            ty, position = self.type_suffix(end + 1, ty)
            ty, _ = self.declarator(start, ty)
            return ty, position
        token = self.tokens[position]
        name = token if token.kind == "IDENT" else None
        if name is not None:
            position += 1
        # Keep the declaration name without mutating the shared integer type.
        ty, position = self.type_suffix(position, ty)
        if ty.kind not in ("STRUCT", "UNION"):
            ty = copy_type(ty)
        ty.name = name
        ty.name_pos = token
        return ty, position

    # abstract-declarator = "*"* ("(" abstract-declarator ")")? type-suffix
    def abstract_declarator(self, position, ty):
        ty, position = self.pointers(position, ty)
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

    def is_end(self, position):
        return self.tokens[position].text == "}" or (
            self.tokens[position].text == "," and self.tokens[position + 1].text == "}")

    def consume_end(self, position):
        if self.tokens[position].text == "}":
            return position + 1
        if self.tokens[position].text == "," and self.tokens[position + 1].text == "}":
            return position + 2
        raise CompileError(self.tokens[position], "expected '}'")

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
        while not self.is_end(position):
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
                value, position = self.const_expr(position + 1)
                value = to_int32(value)
            binding = self.push_scope(token.text)
            binding.enum_ty = ty
            binding.enum_val = value
            value = to_int32(value + 1)
        if tag is not None:
            self.scopes[-1].tags[tag.text] = ty
        return ty, self.consume_end(position)

    # declaration = declspec (declarator ("=" assign)?
    #                        ("," declarator ("=" assign)?)*)? ";"
    def declaration(self, position, basety, attr=None):
        statements = []
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            if ty.kind == "VOID":
                raise CompileError(self.tokens[position], "variable declared void")
            if ty.name is None:
                raise CompileError(ty.name_pos, "variable name omitted")
            if attr is not None and attr.is_static:
                var = self.new_gvar(self.new_unique_name(), ty)
                self.push_scope(ty.name.text).var = var
                if self.tokens[position].text == "=":
                    position = self.gvar_initializer(position + 1, var)
                continue
            var = self.new_lvar(ty.name.text, ty)
            if attr is not None and attr.align:
                var.align = attr.align
            if self.tokens[position].text == "=":
                expression, position = self.lvar_initializer(position + 1, var)
                token = self.tokens[position]
                statements.append(Node("EXPR_STMT", lhs=expression, tok=token))
            if var.ty.size < 0:
                raise CompileError(ty.name, "variable has incomplete type")
            if var.ty.kind == "VOID":
                raise CompileError(ty.name, "variable declared void")
        return Node("BLOCK", body=statements, tok=self.tokens[position]), position + 1

    def skip_excess_element(self, position):
        if self.tokens[position].text == "{":
            position = self.skip_excess_element(position + 1)
            if self.tokens[position].text != "}":
                raise CompileError(self.tokens[position], "expected '}'")
            return position + 1
        _, position = self.assign(position)
        return position

    def string_initializer(self, position, init):
        token = self.tokens[position]
        if init.is_flexible:
            complete = new_initializer(array_of(init.ty.base, token.ty.array_len))
            init.__dict__.update(complete.__dict__)
        count = min(init.ty.array_len, len(token.str))
        for index in range(count):
            byte = token.str[index]
            value = byte if byte < 128 else byte - 256
            init.children[index].expr = Node("NUM", value=value, tok=token)
        return position + 1

    def count_array_init_elements(self, position, ty):
        dummy = new_initializer(ty.base)
        count = 0
        while not self.is_end(position):
            if count:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            position = self.initializer2(position, dummy)
            count += 1
        return count

    def array_initializer(self, position, init):
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        position += 1
        if init.is_flexible:
            count = self.count_array_init_elements(position, init.ty)
            complete = new_initializer(array_of(init.ty.base, count))
            init.__dict__.update(complete.__dict__)
        index = 0
        while not self.is_end(position):
            if index:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            if index < len(init.children):
                position = self.initializer2(position, init.children[index])
            else:
                position = self.skip_excess_element(position)
            index += 1
        return self.consume_end(position)

    def struct_initializer(self, position, init):
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        position += 1
        index = 0
        while not self.is_end(position):
            if index:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            if index < len(init.ty.members):
                member = init.ty.members[index]
                position = self.initializer2(position, init.children[member.idx])
            else:
                position = self.skip_excess_element(position)
            index += 1
        return self.consume_end(position)

    def array_initializer_without_braces(self, position, init):
        if init.is_flexible:
            count = self.count_array_init_elements(position, init.ty)
            init.__dict__.update(new_initializer(array_of(init.ty.base, count)).__dict__)
        for index in range(init.ty.array_len):
            if self.is_end(position):
                break
            if index:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            position = self.initializer2(position, init.children[index])
        return position

    def struct_initializer_without_braces(self, position, init):
        for index, member in enumerate(init.ty.members):
            if self.is_end(position):
                break
            if index:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            position = self.initializer2(position, init.children[member.idx])
        return position

    def union_initializer(self, position, init):
        if not init.children:
            raise CompileError(self.tokens[position], "union has no members")
        if self.tokens[position].text != "{":
            return self.initializer2(position, init.children[0])
        position = self.initializer2(position + 1, init.children[0])
        if self.tokens[position].text == ",":
            position += 1
        if self.tokens[position].text != "}":
            raise CompileError(self.tokens[position], "expected '}'")
        return position + 1

    def initializer2(self, position, init):
        if init.ty.kind == "ARRAY" and self.tokens[position].kind == "STR":
            return self.string_initializer(position, init)
        if init.ty.kind == "ARRAY":
            if self.tokens[position].text == "{":
                return self.array_initializer(position, init)
            return self.array_initializer_without_braces(position, init)
        if init.ty.kind == "STRUCT":
            if self.tokens[position].text == "{":
                return self.struct_initializer(position, init)
            expression, end = self.assign(position)
            add_type(expression)
            if expression.ty.kind == "STRUCT":
                init.expr = expression
                return end
            return self.struct_initializer_without_braces(position, init)
        if init.ty.kind == "UNION":
            return self.union_initializer(position, init)
        if self.tokens[position].text == "{":
            position = self.initializer2(position + 1, init)
            if self.tokens[position].text != "}":
                raise CompileError(self.tokens[position], "expected '}'")
            return position + 1
        init.expr, position = self.assign(position)
        return position

    def initializer(self, position, ty):
        init = new_initializer(ty, is_flexible=True)
        position = self.initializer2(position, init)
        if ty.kind in ("STRUCT", "UNION") and ty.is_flexible:
            complete = copy_type(ty)
            complete.members = [replace(member) for member in ty.members]
            member = complete.members[-1]
            member.ty = init.children[member.idx].ty
            complete.size += member.ty.size
            init.ty = complete
        return init, position

    def init_desg_expr(self, designation, token):
        if designation.var is not None:
            return Node("VAR", var=designation.var, tok=token)
        array = self.init_desg_expr(designation.parent, token)
        if designation.member is not None:
            return Node("MEMBER", lhs=array, member=designation.member, tok=token)
        index = Node("NUM", value=designation.idx, tok=token)
        return Node("DEREF", lhs=new_add(array, index, token), tok=token)

    def create_lvar_init(self, init, ty, designation, token):
        if ty.kind == "ARRAY":
            expression = Node("NULL_EXPR", tok=token)
            for index, child in enumerate(init.children):
                child_designation = InitDesg(parent=designation, idx=index)
                assignment = self.create_lvar_init(child, ty.base, child_designation, token)
                expression = Node("COMMA", expression, assignment, tok=token)
            return expression
        if ty.kind == "STRUCT" and init.expr is None:
            expression = Node("NULL_EXPR", tok=token)
            for member in ty.members:
                child_designation = InitDesg(parent=designation, member=member)
                assignment = self.create_lvar_init(init.children[member.idx], member.ty,
                                                   child_designation, token)
                expression = Node("COMMA", expression, assignment, tok=token)
            return expression
        if ty.kind == "UNION":
            member = ty.members[0]
            child_designation = InitDesg(parent=designation, member=member)
            return self.create_lvar_init(init.children[0], member.ty, child_designation, token)
        if init.expr is None:
            return Node("NULL_EXPR", tok=token)
        target = self.init_desg_expr(designation, token)
        return Node("ASSIGN", target, init.expr, tok=token)

    def lvar_initializer(self, position, var):
        token = self.tokens[position]
        init, position = self.initializer(position, var.ty)
        var.ty = init.ty
        expression = self.create_lvar_init(init, var.ty, InitDesg(var=var), token)
        zero = Node("MEMZERO", var=var, tok=token)
        return Node("COMMA", zero, expression, tok=token), position

    def write_gvar_data(self, init, ty, buffer, offset, relocations):
        if ty.kind == "ARRAY":
            for index, child in enumerate(init.children):
                self.write_gvar_data(child, ty.base, buffer, offset + ty.base.size * index, relocations)
            return
        if ty.kind == "STRUCT":
            for member in ty.members:
                self.write_gvar_data(init.children[member.idx], member.ty,
                                     buffer, offset + member.offset, relocations)
            return
        if ty.kind == "UNION":
            self.write_gvar_data(init.children[0], ty.members[0].ty, buffer, offset, relocations)
            return
        if init.expr is not None:
            value, label = evaluate_initializer(init.expr)
            if label is not None:
                relocations.append(Relocation(offset, label, value))
                return
            if ty.size not in (1, 2, 4, 8):
                raise CompileError(init.expr.tok, "unsupported initializer size")
            value &= (1 << (ty.size * 8)) - 1
            buffer[offset:offset + ty.size] = value.to_bytes(ty.size, "little")

    def gvar_initializer(self, position, var):
        init, position = self.initializer(position, var.ty)
        var.ty = init.ty
        buffer = bytearray(var.ty.size)
        self.write_gvar_data(init, var.ty, buffer, 0, var.relocations)
        var.init_data = bytes(buffer)
        return position

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
                if self.is_function(position):
                    position = self.function(position, basety, attr)
                    continue
                if attr.is_extern:
                    position = self.global_variable(position, basety, attr)
                    continue
                node, position = self.declaration(position, basety, attr)
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
        if ty.name is None:
            raise CompileError(ty.name_pos, "function name omitted")
        function = self.new_gvar(ty.name.text, ty)
        function.is_function = True
        function.is_definition = False
        function.is_static = attr.is_static
        if self.tokens[position].text == ";":
            return position + 1
        function.is_definition = True
        self.current_fn = function
        self.locals = []
        self.enter_scope()
        for param in reversed(ty.params):
            if param.name is None:
                raise CompileError(param.name_pos, "parameter name omitted")
            self.new_lvar(param.name.text, param)
        function.params = self.locals.copy()
        if ty.is_variadic:
            function.va_area = self.new_lvar("__va_area__", array_of(ty_char, 136))
        if self.tokens[position].text != "{":
            raise CompileError(self.tokens[position], "expected '{'")
        function.body, position = self.compound_stmt(position + 1)
        function.locals = self.locals
        self.leave_scope()
        self.resolve_goto_labels()
        return position

    def global_variable(self, position, basety, attr):
        first = True
        while self.tokens[position].text != ";":
            if not first:
                if self.tokens[position].text != ",":
                    raise CompileError(self.tokens[position], "expected ','")
                position += 1
            first = False
            ty, position = self.declarator(position, basety)
            if ty.name is None:
                raise CompileError(ty.name_pos, "variable name omitted")
            var = self.new_gvar(ty.name.text, ty)
            var.is_definition = not attr.is_extern
            var.is_static = attr.is_static
            if attr.align:
                var.align = attr.align
            if self.tokens[position].text == "=":
                position = self.gvar_initializer(position + 1, var)
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
            if ty.name is None:
                raise CompileError(ty.name_pos, "typedef name omitted")
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
                position = self.global_variable(position, basety, attr)
        return self.globals


def parse(tokens):
    return Parser(tokens).parse()
