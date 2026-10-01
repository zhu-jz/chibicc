"""Read quoted includes and remove null directives before keyword conversion.

Based on chibicc commit d367510fcc1396fa252c4b87439c2f9fcd0abbe7.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import os
from dataclasses import dataclass, replace

from tokenizer import convert_keywords, tokenize_file, warn_tok
from common import CompileError
from parse import const_expr


@dataclass
class CondIncl:
    tok: object
    included: bool
    context: str = "THEN"


@dataclass
class Macro:
    name: str
    body: list
    is_objlike: bool = True


def skip_line(tokens, position):
    if not tokens[position].at_bol:
        warn_tok(tokens[position], "extra token")
    # The original inverted loop never advances after this warning.
    return position


def is_hash(token):
    return token.at_bol and token.text == "#"


def skip_cond_incl2(tokens, position):
    while tokens[position].kind != "EOF":
        if is_hash(tokens[position]) and tokens[position + 1].text in ("if", "ifdef", "ifndef"):
            position = skip_cond_incl2(tokens, position + 2)
            continue
        if is_hash(tokens[position]) and tokens[position + 1].text == "endif":
            return min(position + 2, len(tokens) - 1)
        position += 1
    return position


def skip_cond_incl(tokens, position):
    while tokens[position].kind != "EOF":
        if is_hash(tokens[position]) and tokens[position + 1].text in ("if", "ifdef", "ifndef"):
            position = skip_cond_incl2(tokens, position + 2)
            continue
        if is_hash(tokens[position]) and tokens[position + 1].text in ("elif", "else", "endif"):
            break
        position += 1
    return position


def copy_line(tokens, position):
    start = position
    while tokens[position].kind != "EOF" and not tokens[position].at_bol:
        position += 1
    line = [replace(token) for token in tokens[start:position]]
    line.append(replace(tokens[position], kind="EOF", text=""))
    return line, position


def eval_const_expr(tokens, position, files, macros, conditions):
    start = tokens[position]
    expression, position = copy_line(tokens, position + 1)
    preprocess2(expression, files, macros, conditions)
    if expression[0].kind == "EOF":
        raise CompileError(start, "no expression")
    value, rest = const_expr(expression)
    if expression[rest].kind != "EOF":
        raise CompileError(expression[rest], "extra token")
    return value, position


def find_macro(token, macros):
    if token.kind == "IDENT":
        return macros.get(token.text)
    return None


def add_hideset(tokens, hideset):
    return [replace(token, hideset=token.hideset | hideset) for token in tokens]


def read_macro_definition(tokens, position, macros):
    name = tokens[position]
    if name.kind != "IDENT":
        raise CompileError(name, "macro name must be an identifier")
    position += 1
    is_objlike = tokens[position].has_space or tokens[position].text != "("
    if not is_objlike:
        position += 1
        if tokens[position].text != ")":
            raise CompileError(tokens[position], "expected ')'")
        position += 1
    body, position = copy_line(tokens, position)
    macros[name.text] = Macro(name.text, body, is_objlike)
    return position


def expand_macro(tokens, position, macros):
    token = tokens[position]
    if token.text in token.hideset:
        return False
    macro = find_macro(token, macros)
    if macro is None:
        return False
    if not macro.is_objlike:
        if tokens[position + 1].text != "(":
            return False
        if tokens[position + 2].text != ")":
            raise CompileError(tokens[position + 2], "expected ')'")
        tokens[position:position + 3] = [replace(tok) for tok in macro.body[:-1]]
        return True
    hideset = token.hideset | {macro.name}
    tokens[position:position + 1] = add_hideset(macro.body[:-1], hideset)
    return True


def preprocess2(tokens, files, macros, conditions):
    result = []
    position = 0
    while tokens[position].kind != "EOF":
        if expand_macro(tokens, position, macros):
            continue
        token = tokens[position]
        if is_hash(token):
            position += 1
            if tokens[position].text == "include":
                filename = tokens[position + 1]
                if filename.kind != "STR":
                    raise CompileError(filename, "expected a filename")
                including_file = filename.file.name if filename.file else "-"
                directory = os.path.dirname(including_file) or "."
                name = os.fsdecode(filename.str.split(b"\0", 1)[0])
                path = name if name.startswith("/") else directory + "/" + name
                try:
                    included = tokenize_file(path, files)
                except CompileError as error:
                    if error.position is None:
                        raise CompileError(filename, str(error)) from None
                    raise
                rest = skip_line(tokens, position + 2)
                tokens[position - 1:rest] = [replace(tok) for tok in included[:-1]]
                position -= 1
                continue
            if tokens[position].text == "define":
                position = read_macro_definition(tokens, position + 1, macros)
                continue
            if tokens[position].text == "undef":
                name = tokens[position + 1]
                if name.kind != "IDENT":
                    raise CompileError(name, "macro name must be an identifier")
                position = skip_line(tokens, position + 2)
                macros.pop(name.text, None)
                continue
            if tokens[position].text == "if":
                value, position = eval_const_expr(tokens, position, files, macros, conditions)
                conditions.append(CondIncl(token, bool(value)))
                if not value:
                    position = skip_cond_incl(tokens, position)
                continue
            if tokens[position].text in ("ifdef", "ifndef"):
                directive = tokens[position]
                defined = find_macro(tokens[position + 1], macros) is not None
                included = defined if directive.text == "ifdef" else not defined
                conditions.append(CondIncl(directive, included))
                position = skip_line(tokens, min(position + 2, len(tokens) - 1))
                if not included:
                    position = skip_cond_incl(tokens, position)
                continue
            if tokens[position].text == "elif":
                if not conditions or conditions[-1].context == "ELSE":
                    raise CompileError(token, "stray #elif")
                conditions[-1].context = "ELIF"
                if conditions[-1].included:
                    position = skip_cond_incl(tokens, position)
                else:
                    value, position = eval_const_expr(tokens, position, files, macros, conditions)
                    if value:
                        conditions[-1].included = True
                    else:
                        position = skip_cond_incl(tokens, position)
                continue
            if tokens[position].text == "else":
                if not conditions or conditions[-1].context == "ELSE":
                    raise CompileError(token, "stray #else")
                conditions[-1].context = "ELSE"
                position = skip_line(tokens, position + 1)
                if conditions[-1].included:
                    position = skip_cond_incl(tokens, position)
                continue
            if tokens[position].text == "endif":
                if not conditions:
                    raise CompileError(token, "stray #endif")
                conditions.pop()
                position = skip_line(tokens, position + 1)
                continue
            if tokens[position].at_bol:
                continue
            raise CompileError(tokens[position], "invalid preprocessor directive")
        result.append(token)
        position += 1
    result.append(tokens[position])
    tokens[:] = result
    return tokens


def preprocess(tokens, files=None):
    if files is None:
        files = []
    conditions = []
    preprocess2(tokens, files, {}, conditions)
    if conditions:
        raise CompileError(conditions[-1].tok, "unterminated conditional directive")
    convert_keywords(tokens)
    return tokens
