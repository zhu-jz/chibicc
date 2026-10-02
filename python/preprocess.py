"""Read quoted includes and remove null directives before keyword conversion.

Based on chibicc commit d367510fcc1396fa252c4b87439c2f9fcd0abbe7.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import os
import time
from dataclasses import dataclass, field, replace

from tokenizer import convert_pp_tokens, tokenize, tokenize_file, warn_tok, tokenize_string_literal
from common import CompileError, File
from parse import const_expr
from type import array_of


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
    handler: object = None
    va_args_name: str = None


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
    convert_pp_tokens(expression)
    value, rest = const_expr(expression)
    if expression[rest].kind != "EOF":
        raise CompileError(expression[rest], "extra token")
    return value, position


def find_macro(token, macros):
    # A dictionary provides the name hash table introduced in original lesson 286.
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
    va_args_name = None
    if not is_objlike:
        params, va_args_name, position = read_macro_params(tokens, position + 1)
    body, position = copy_line(tokens, position)
    macros[name.text] = Macro(name.text, body, is_objlike, params, va_args_name=va_args_name)
    return position


def read_macro_params(tokens, position):
    params = []
    while tokens[position].text != ")":
        if params:
            if tokens[position].text != ",":
                raise CompileError(tokens[position], "expected ','")
            position += 1
        if tokens[position].text == "...":
            position += 1
            if tokens[position].text != ")":
                raise CompileError(tokens[position], "expected ')'")
            return params, "__VA_ARGS__", position + 1
        if tokens[position].kind != "IDENT":
            raise CompileError(tokens[position], "expected an identifier")
        if tokens[position + 1].text == "...":
            name = tokens[position].text
            position += 2
            if tokens[position].text != ")":
                raise CompileError(tokens[position], "expected ')'")
            return params, name, position + 1
        params.append(tokens[position].text)
        position += 1
    return params, None, position + 1


def read_macro_arg_one(tokens, position, read_rest=False):
    argument = []
    level = 0
    while True:
        if level == 0 and tokens[position].text == ")":
            break
        if level == 0 and not read_rest and tokens[position].text == ",":
            break
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


def read_macro_args(tokens, position, params, va_args_name=None):
    position += 2
    args = {}
    for index, name in enumerate(params):
        if index:
            if tokens[position].text != ",":
                raise CompileError(tokens[position], "expected ','")
            position += 1
        argument, position = read_macro_arg_one(tokens, position)
        args.setdefault(name, argument)
    if va_args_name:
        if tokens[position].text == ")":
            argument = [replace(tokens[position], kind="EOF", text="")]
        else:
            if params:
                if tokens[position].text != ",":
                    raise CompileError(tokens[position], "expected ','")
                position += 1
            argument, position = read_macro_arg_one(tokens, position, read_rest=True)
        args[va_args_name] = argument
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


def subst(body, args, files, macros, conditions, include_paths, va_args_name=None):
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
        if token.text == "," and body[position + 1].text == "##":
            name = body[position + 2].text
            argument = args.get(name)
            if name == va_args_name and argument is not None:
                if argument[0].kind == "EOF":
                    position += 3
                else:
                    result.append(replace(token))
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
        if token.text == "__VA_OPT__" and body[position + 1].text == "(":
            optional, position = read_macro_arg_one(body, position + 2, read_rest=True)
            varargs = args.get("__VA_ARGS__")
            if varargs is not None and varargs[0].kind != "EOF":
                result.extend(replace(tok) for tok in optional[:-1])
            if body[position].text != ")":
                raise CompileError(body[position], "expected ')'")
            position += 1
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
    if macro.handler is not None:
        tokens[position] = macro.handler(token)
        return True
    if not macro.is_objlike:
        if tokens[position + 1].text != "(":
            return False
        args, rest = read_macro_args(tokens, position, macro.params, macro.va_args_name)
        hideset = (token.hideset & tokens[rest - 1].hideset) | {macro.name}
        body = subst(macro.body, args, files, macros, conditions, include_paths, macro.va_args_name)
        body = add_hideset(body[:-1], hideset)
        for replacement in body:
            replacement.origin = token
        tokens[position:rest] = body
        tokens[position].at_bol = token.at_bol
        tokens[position].has_space = token.has_space
        return True
    hideset = token.hideset | {macro.name}
    body = add_hideset(macro.body[:-1], hideset)
    for replacement in body:
        replacement.origin = token
    tokens[position:position + 1] = body
    tokens[position].at_bol = token.at_bol
    tokens[position].has_space = token.has_space
    return True


include_search_cache = {}


def search_include_paths(filename, include_paths):
    if filename.startswith("/"):
        return filename
    key = (filename, tuple(include_paths))
    if key in include_search_cache:
        return include_search_cache[key]
    for directory in include_paths:
        path = directory + "/" + filename
        if os.path.exists(path):
            include_search_cache[key] = path
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


include_guard_cache = {}


def detect_include_guard(tokens):
    if len(tokens) < 7 or not is_hash(tokens[0]) or tokens[1].text != "ifndef":
        return None
    name = tokens[2]
    if name.kind != "IDENT":
        return None
    if not is_hash(tokens[3]) or tokens[4].text != "define" or tokens[5].text != name.text:
        return None
    # The original scans directives without successfully skipping nested groups.
    for position in range(3, len(tokens) - 2):
        if (is_hash(tokens[position]) and tokens[position + 1].text == "endif"
                and tokens[position + 2].kind == "EOF"):
            return name.text
    return None


def include_file(path, filename, files, macros):
    guard = include_guard_cache.get(path)
    if guard is not None and guard in macros:
        return []
    try:
        included = tokenize_file(path, files)
    except CompileError as error:
        if error.position is None:
            raise CompileError(filename, str(error)) from None
        raise
    guard = detect_include_guard(included)
    if guard is not None:
        include_guard_cache[path] = guard
    return included


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
                included = include_file(path, filename, files, macros)
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
                undef_macro(macros, name.text)
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
            if tokens[position].text == "error":
                raise CompileError(tokens[position], "error")
            if tokens[position].text == "line":
                position = read_line_marker(tokens, position + 1, files, macros, include_paths)
                continue
            if tokens[position].kind == "PP_NUM":
                position = read_line_marker(tokens, position, files, macros, include_paths)
                continue
            if tokens[position].text == "pragma":
                _, position = copy_line(tokens, position + 1)
                continue
            if tokens[position].at_bol:
                continue
            raise CompileError(tokens[position], "invalid preprocessor directive")
        if token.file is not None:
            token.line_delta = token.file.line_delta
            token.filename = token.file.display_name
        result.append(token)
        position += 1
    result.append(tokens[position])
    tokens[:] = result
    return tokens


def read_line_marker(tokens, position, files, macros, include_paths):
    start = tokens[position]
    line, rest = copy_line(tokens, position)
    preprocess(line, files, include_paths, macros)
    if line[0].kind != "NUM" or line[0].ty.kind != "INT":
        raise CompileError(line[0], "invalid line marker")
    start.file.line_delta = line[0].value - start.line_no
    if line[1].kind == "EOF":
        return rest
    if line[1].kind != "STR":
        raise CompileError(line[1], "filename expected")
    start.file.display_name = line[1].str.split(b"\0", 1)[0].decode('utf-8', errors='replace')
    return rest


def file_macro(template):
    while template.origin is not None:
        template = template.origin
    return new_str_token(template.file.display_name if template.file else "-", template)


def line_macro(template):
    while template.origin is not None:
        template = template.origin
    return new_num_token(template.line_no + (template.file.line_delta if template.file else 0), template)


def timestamp_macro(template):
    try:
        modified = os.stat(template.file.name).st_mtime
    except OSError:
        return new_str_token("??? ??? ?? ??:??:?? ????", template)
    return new_str_token(time.ctime(modified)[:24], template)


def undef_macro(macros, name):
    # Delete the entry directly; no linked-list deletion marker is needed.
    macros.pop(name, None)


def define_macro(macros, name, source):
    file = File("<built-in>", 1, source)
    tokens = tokenize(source)
    for token in tokens:
        token.file = file
    macros[name] = Macro(name, tokens)


def init_macros(base_file="-"):
    definitions = {
        '_LP64': '1',
        '__C99_MACRO_WITH_VA_ARGS': '1',
        '__ELF__': '1',
        '__LP64__': '1',
        '__SIZEOF_DOUBLE__': '8',
        '__SIZEOF_FLOAT__': '4',
        '__SIZEOF_INT__': '4',
        '__SIZEOF_LONG_DOUBLE__': '8',
        '__SIZEOF_LONG_LONG__': '8',
        '__SIZEOF_LONG__': '8',
        '__SIZEOF_POINTER__': '8',
        '__SIZEOF_PTRDIFF_T__': '8',
        '__SIZEOF_SHORT__': '2',
        '__SIZEOF_SIZE_T__': '8',
        '__SIZE_TYPE__': 'unsigned long',
        '__STDC_HOSTED__': '1',
        '__STDC_NO_ATOMICS__': '1',
        '__STDC_NO_COMPLEX__': '1',
        '__STDC_UTF_16__': '1',
        '__STDC_UTF_32__': '1',
        '__STDC_VERSION__': '201112L',
        '__STDC__': '1',
        '__USER_LABEL_PREFIX__': '',
        '__alignof__': '_Alignof',
        '__amd64': '1',
        '__amd64__': '1',
        '__chibicc__': '1',
        '__const__': 'const',
        '__gnu_linux__': '1',
        '__inline__': 'inline',
        '__linux': '1',
        '__linux__': '1',
        '__signed__': 'signed',
        '__typeof__': 'typeof',
        '__unix': '1',
        '__unix__': '1',
        '__volatile__': 'volatile',
        '__x86_64': '1',
        '__x86_64__': '1',
        'linux': '1',
        'unix': '1',
    }
    macros = {}
    for name, source in definitions.items():
        define_macro(macros, name, source)
    macros["__FILE__"] = Macro("__FILE__", [], handler=file_macro)
    macros["__LINE__"] = Macro("__LINE__", [], handler=line_macro)
    counter = 0

    def counter_macro(template):
        nonlocal counter
        token = new_num_token(counter, template)
        counter += 1
        return token

    macros["__COUNTER__"] = Macro("__COUNTER__", [], handler=counter_macro)
    macros["__TIMESTAMP__"] = Macro("__TIMESTAMP__", [], handler=timestamp_macro)
    macros["__BASE_FILE__"] = Macro("__BASE_FILE__", [],
                                   handler=lambda template: new_str_token(base_file, template))
    now = time.localtime()
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    define_macro(macros, "__DATE__", f'"{months[now.tm_mon - 1]} {now.tm_mday:2d} {now.tm_year}"')
    define_macro(macros, "__TIME__", f'"{now.tm_hour:02d}:{now.tm_min:02d}:{now.tm_sec:02d}"')
    return macros


def get_string_kind(token):
    # Retain the original exact-spelling u8 check at this historical step.
    if token.text == "u8":
        return "UTF8"
    return {'"': "NONE", 'u': "UTF16", 'U': "UTF32", 'L': "WIDE"}[token.text[0]]


def join_adjacent_string_literals(tokens):
    position = 0
    while tokens[position].kind != "EOF":
        first = tokens[position]
        if first.kind != "STR" or tokens[position + 1].kind != "STR":
            position += 1
            continue
        end = position + 1
        while tokens[end].kind == "STR":
            end += 1
        kind, basety = get_string_kind(first), first.ty.base
        for token in tokens[position + 1:end]:
            next_kind = get_string_kind(token)
            if kind == "NONE":
                kind, basety = next_kind, token.ty.base
            elif next_kind != "NONE" and kind != next_kind:
                raise CompileError(token, "unsupported non-standard concatenation of string literals")
        if basety.size > 1:
            for token in tokens[position:end]:
                if token.ty.base.size == 1:
                    converted = tokenize_string_literal(token, basety)
                    token.ty, token.str = converted.ty, converted.str
        size = first.ty.base.size
        data = b"".join(token.str[:-token.ty.base.size] for token in tokens[position:end]) + b"\0" * size
        first.ty = array_of(first.ty.base, len(data) // size)
        first.str = data
        del tokens[position + 1:end]
        position += 1


def preprocess(tokens, files=None, include_paths=(), macros=None):
    if files is None:
        files = []
    conditions = []
    if macros is None:
        base_file = files[0].name if files else tokens[0].file.name
        macros = init_macros(base_file)
    preprocess2(tokens, files, macros, conditions, include_paths)
    if conditions:
        raise CompileError(conditions[-1].tok, "unterminated conditional directive")
    convert_pp_tokens(tokens)
    join_adjacent_string_literals(tokens)
    for token in tokens:
        token.line_no += token.line_delta
    return tokens
