"""Read quoted includes and remove null directives before keyword conversion.

Based on chibicc commit d367510fcc1396fa252c4b87439c2f9fcd0abbe7.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import os
from dataclasses import dataclass, field, replace

from tokenizer import convert_keywords, tokenize, tokenize_file, warn_tok
from common import CompileError, File
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
    params: list[str] = field(default_factory=list)


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


def eval_const_expr(tokens, position, files, macros, conditions, include_paths):
    start = tokens[position]
    expression, position = read_const_expr(tokens, position + 1, macros)
    preprocess2(expression, files, macros, conditions, include_paths)
    if expression[0].kind == "EOF":
        raise CompileError(start, "no expression")
    for index, token in enumerate(expression):
        if token.kind == "IDENT":
            expression[index] = new_num_token(0, token)
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
    params = []
    if not is_objlike:
        params, position = read_macro_params(tokens, position + 1)
    body, position = copy_line(tokens, position)
    macros[name.text] = Macro(name.text, body, is_objlike, params)
    return position


def read_macro_params(tokens, position):
    params = []
    while tokens[position].text != ")":
        if params:
            if tokens[position].text != ",":
                raise CompileError(tokens[position], "expected ','")
            position += 1
        if tokens[position].kind != "IDENT":
            raise CompileError(tokens[position], "expected an identifier")
        params.append(tokens[position].text)
        position += 1
    return params, position + 1


def read_macro_arg_one(tokens, position):
    argument = []
    level = 0
    while level > 0 or tokens[position].text not in (",", ")"):
        if tokens[position].kind == "EOF":
            raise CompileError(tokens[position], "premature end of input")
        if tokens[position].text == "(":
            level += 1
        elif tokens[position].text == ")":
            level -= 1
        argument.append(replace(tokens[position]))
        position += 1
    argument.append(replace(tokens[position], kind="EOF", text=""))
    return argument, position


def read_macro_args(tokens, position, params):
    position += 2
    args = {}
    for index, name in enumerate(params):
        if index:
            if tokens[position].text != ",":
                raise CompileError(tokens[position], "expected ','")
            position += 1
        argument, position = read_macro_arg_one(tokens, position)
        args.setdefault(name, argument)
    if tokens[position].text != ")":
        raise CompileError(tokens[position], "expected ')'")
    return args, position + 1


def quote_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def new_str_token(text, template):
    return tokenize_like(quote_string(text), template)[0]


def tokenize_like(source, template):
    file = None
    if template.file is not None:
        file = File(template.file.name, template.file.file_no, source)
    try:
        tokens = tokenize(source)
    except CompileError as error:
        error.file = file
        raise
    if file is not None:
        for token in tokens:
            token.file = file
    return tokens


def new_num_token(value, template):
    return tokenize_like(f"{value}\n", template)[0]


def read_const_expr(tokens, position, macros):
    line, rest = copy_line(tokens, position)
    result = []
    position = 0
    while line[position].kind != "EOF":
        start = line[position]
        if start.text != "defined":
            result.append(start)
            position += 1
            continue
        position += 1
        has_paren = line[position].text == "("
        if has_paren:
            position += 1
        if line[position].kind != "IDENT":
            raise CompileError(start, "macro name must be an identifier")
        defined = find_macro(line[position], macros) is not None
        position += 1
        if has_paren:
            if line[position].text != ")":
                raise CompileError(line[position], "expected ')'")
            position += 1
        result.append(new_num_token(int(defined), start))
    result.append(line[position])
    return result, rest


def join_tokens(tokens, end=None):
    parts = []
    for index, token in enumerate(tokens):
        if index == end:
            break
        if token.kind == "EOF":
            break
        if index and token.has_space:
            parts.append(" ")
        parts.append(token.text)
    return "".join(parts)


def paste(lhs, rhs):
    text = lhs.text + rhs.text
    tokens = tokenize_like(text, lhs)
    if len(tokens) != 2 or tokens[0].kind == "EOF":
        raise CompileError(lhs, f"pasting forms '{text}', an invalid token")
    return tokens[0]


def subst(body, args, files, macros, conditions, include_paths):
    result = []
    position = 0
    while body[position].kind != "EOF":
        token = body[position]
        if token.text == "#":
            argument = args.get(body[position + 1].text)
            if argument is None:
                raise CompileError(body[position + 1], "'#' is not followed by a macro parameter")
            result.append(new_str_token(join_tokens(argument), token))
            position += 2
            continue
        if token.text == "##":
            if not result:
                raise CompileError(token, "'##' cannot appear at start of macro expansion")
            rhs = body[position + 1]
            if rhs.kind == "EOF":
                raise CompileError(token, "'##' cannot appear at end of macro expansion")
            argument = args.get(rhs.text)
            if argument is not None:
                if argument[0].kind != "EOF":
                    result[-1] = paste(result[-1], argument[0])
                    result.extend(replace(tok) for tok in argument[1:-1])
            else:
                result[-1] = paste(result[-1], rhs)
            position += 2
            continue
        argument = args.get(token.text)
        if argument is not None and body[position + 1].text == "##":
            rhs = body[position + 2]
            if rhs.kind == "EOF":
                raise CompileError(body[position + 1], "'##' cannot appear at end of macro expansion")
            if argument[0].kind == "EOF":
                other = args.get(rhs.text)
                if other is not None:
                    result.extend(replace(tok) for tok in other[:-1])
                else:
                    result.append(replace(rhs))
                position += 3
            else:
                result.extend(replace(tok) for tok in argument[:-1])
                position += 1
            continue
        if argument is not None:
            expanded = [replace(tok) for tok in argument]
            preprocess2(expanded, files, macros, conditions, include_paths)
            expanded[0].at_bol = token.at_bol
            expanded[0].has_space = token.has_space
            result.extend(replace(tok) for tok in expanded[:-1])
        else:
            result.append(replace(token))
        position += 1
    result.append(body[-1])
    return result


def expand_macro(tokens, position, files, macros, conditions, include_paths):
    token = tokens[position]
    if token.text in token.hideset:
        return False
    macro = find_macro(token, macros)
    if macro is None:
        return False
    if not macro.is_objlike:
        if tokens[position + 1].text != "(":
            return False
        args, rest = read_macro_args(tokens, position, macro.params)
        hideset = (token.hideset & tokens[rest - 1].hideset) | {macro.name}
        body = subst(macro.body, args, files, macros, conditions, include_paths)
        tokens[position:rest] = add_hideset(body[:-1], hideset)
        tokens[position].at_bol = token.at_bol
        tokens[position].has_space = token.has_space
        return True
    hideset = token.hideset | {macro.name}
    tokens[position:position + 1] = add_hideset(macro.body[:-1], hideset)
    tokens[position].at_bol = token.at_bol
    tokens[position].has_space = token.has_space
    return True


def search_include_paths(filename, include_paths):
    if filename.startswith("/"):
        return filename
    for directory in include_paths:
        path = directory + "/" + filename
        if os.path.exists(path):
            return path
    return None


def read_include_filename(tokens, position, files, macros, conditions, include_paths):
    token = tokens[position]
    if token.kind == "STR":
        return token.text[1:-1], True, skip_line(tokens, position + 1)
    if token.text == "<":
        start = position + 1
        while tokens[position].text != ">":
            if tokens[position].at_bol or tokens[position].kind == "EOF":
                raise CompileError(tokens[position], "expected '>'")
            position += 1
        name = join_tokens(tokens[start:position])
        return name, False, skip_line(tokens, position + 1)
    if token.kind == "IDENT":
        line, rest = copy_line(tokens, position)
        preprocess2(line, files, macros, conditions, include_paths)
        name, is_dquote, _ = read_include_filename(line, 0, files, macros, conditions, include_paths)
        return name, is_dquote, rest
    raise CompileError(token, "expected a filename")


def preprocess2(tokens, files, macros, conditions, include_paths):
    result = []
    position = 0
    while tokens[position].kind != "EOF":
        if expand_macro(tokens, position, files, macros, conditions, include_paths):
            continue
        token = tokens[position]
        if is_hash(token):
            position += 1
            if tokens[position].text == "include":
                filename = tokens[position + 1]
                name, is_dquote, rest = read_include_filename(tokens, position + 1, files, macros, conditions, include_paths)
                including_file = token.file.name if token.file else "-"
                directory = os.path.dirname(including_file) or "."
                path = name
                if not name.startswith("/"):
                    if is_dquote and os.path.exists(directory + "/" + name):
                        path = directory + "/" + name
                    else:
                        path = search_include_paths(name, include_paths) or name
                try:
                    included = tokenize_file(path, files)
                except CompileError as error:
                    if error.position is None:
                        raise CompileError(filename, str(error)) from None
                    raise
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
                value, position = eval_const_expr(tokens, position, files, macros, conditions, include_paths)
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
                    value, position = eval_const_expr(tokens, position, files, macros, conditions, include_paths)
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


def preprocess(tokens, files=None, include_paths=()):
    if files is None:
        files = []
    conditions = []
    preprocess2(tokens, files, {}, conditions, include_paths)
    if conditions:
        raise CompileError(conditions[-1].tok, "unterminated conditional directive")
    convert_keywords(tokens)
    return tokens
