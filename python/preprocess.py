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


def skip_line(tokens, position):
    if not tokens[position].at_bol:
        warn_tok(tokens[position], "extra token")
    # The original inverted loop never advances after this warning.
    return position


def is_hash(token):
    return token.at_bol and token.text == "#"


def skip_cond_incl2(tokens, position):
    while tokens[position].kind != "EOF":
        if is_hash(tokens[position]) and tokens[position + 1].text == "if":
            position = skip_cond_incl2(tokens, position + 2)
            continue
        if is_hash(tokens[position]) and tokens[position + 1].text == "endif":
            return min(position + 2, len(tokens) - 1)
        position += 1
    return position


def skip_cond_incl(tokens, position):
    while tokens[position].kind != "EOF":
        if is_hash(tokens[position]) and tokens[position + 1].text == "if":
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


def eval_const_expr(tokens, position):
    start = tokens[position]
    expression, position = copy_line(tokens, position + 1)
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


def expand_macro(tokens, position, macros):
    macro = find_macro(tokens[position], macros)
    if macro is None:
        return False
    tokens[position:position + 1] = [replace(token) for token in macro.body[:-1]]
    return True


def preprocess(tokens, files=None):
    if files is None:
        files = []
    result = []
    conditions = []
    macros = {}
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
                name = tokens[position + 1]
                if name.kind != "IDENT":
                    raise CompileError(name, "macro name must be an identifier")
                body, position = copy_line(tokens, position + 2)
                macros[name.text] = Macro(name.text, body)
                continue
            if tokens[position].text == "undef":
                name = tokens[position + 1]
                if name.kind != "IDENT":
                    raise CompileError(name, "macro name must be an identifier")
                position = skip_line(tokens, position + 2)
                macros.pop(name.text, None)
                continue
            if tokens[position].text == "if":
                value, position = eval_const_expr(tokens, position)
                conditions.append(CondIncl(token, bool(value)))
                if not value:
                    position = skip_cond_incl(tokens, position)
                continue
            if tokens[position].text == "elif":
                if not conditions or conditions[-1].context == "ELSE":
                    raise CompileError(token, "stray #elif")
                conditions[-1].context = "ELIF"
                if conditions[-1].included:
                    position = skip_cond_incl(tokens, position)
                else:
                    value, position = eval_const_expr(tokens, position)
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
    if conditions:
        raise CompileError(conditions[-1].tok, "unterminated conditional directive")
    tokens[:] = result
    convert_keywords(tokens)
    return tokens
