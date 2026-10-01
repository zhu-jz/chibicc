"""Turn source characters into tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import string
import re
import sys
from unicode import is_ident1, is_ident2

from common import CompileError, Token, File, format_diagnostic, to_int32
from type import array_of, ty_char, ty_int, ty_long, ty_uint, ty_ulong, ty_ushort
from type import ty_float, ty_double


def read_file(path):
    try:
        if path == "-":
            source = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(path, encoding="utf-8", newline="") as input_file:
                source = input_file.read()
    except OSError as error:
        raise CompileError(None, f"cannot open {path}: {error.strerror}") from None
    except UnicodeError:
        raise CompileError(None, f"cannot decode {path} as UTF-8") from None
    if not source.endswith("\n"):
        source += "\n"
    return source


def canonicalize_newline(source):
    return source.replace("\r\n", "\n").replace("\r", "\n")


def remove_backslash_newline(source):
    result = []
    position = 0
    pending_newlines = 0
    while position < len(source):
        if source.startswith("\\\n", position):
            position += 2
            pending_newlines += 1
            continue
        character = source[position]
        result.append(character)
        position += 1
        if character == "\n":
            result.append("\n" * pending_newlines)
            pending_newlines = 0
    result.append("\n" * pending_newlines)
    return "".join(result)


def convert_universal_chars(source):
    result = []
    position = 0
    while position < len(source):
        length = 4 if source.startswith("\\u", position) else 8 if source.startswith("\\U", position) else 0
        if length:
            digits = source[position + 2:position + 2 + length]
            if len(digits) == length and all(c in string.hexdigits for c in digits):
                value = int(digits, 16)
                if value:
                    if value > 0x10ffff or 0xd800 <= value <= 0xdfff:
                        raise CompileError(position, "invalid Unicode code point")
                    result.append(chr(value))
                    position += length + 2
                    continue
            result.append(source[position])
            position += 1
        elif source[position] == "\\":
            result.append(source[position:position + 2])
            position += 2
        else:
            result.append(source[position])
            position += 1
    return "".join(result)


def tokenize_file(path, files):
    path = str(path)
    source = read_file(path)
    if source.startswith("\ufeff"):
        source = source[1:]
    source = remove_backslash_newline(canonicalize_newline(source))
    file = File(path, len(files) + 1, source)
    files.append(file)
    try:
        source = convert_universal_chars(source)
        file.contents = source
        tokens = tokenize(source)
    except CompileError as error:
        error.file = file
        raise
    for token in tokens:
        token.file = file
        token.filename = file.display_name
    return tokens


def warn_tok(token: Token, message: str) -> None:
    if token.file is None:
        print(message, file=sys.stderr)
    else:
        print(format_diagnostic(token.file, token.position, message, token.line_no), file=sys.stderr)


def read_escaped_char(source, position):
    character = source[position]
    if "0" <= character <= "7":
        value = 0
        count = 0
        while position < len(source) and "0" <= source[position] <= "7" and count < 3:
            value = value * 8 + int(source[position])
            position += 1
            count += 1
        return value, position
    if character == "x":
        position += 1
        if position >= len(source) or source[position] not in string.hexdigits:
            raise CompileError(position, "invalid hex escape sequence")
        value = 0
        while position < len(source) and source[position] in string.hexdigits:
            value = value * 16 + int(source[position], 16)
            position += 1
        return value, position
    escapes = {"a": 7, "b": 8, "t": 9, "n": 10,
               "v": 11, "f": 12, "r": 13, "e": 27}
    return escapes.get(character, ord(character)), position + 1


def string_literal_end(source, position):
    start = position
    while position < len(source) and source[position] != '"':
        if source[position] in ("\n", "\0"):
            raise CompileError(start, "unclosed string literal")
        if source[position] == "\\":
            position += 1
        position += 1
    if position >= len(source):
        raise CompileError(start, "unclosed string literal")
    return position


def read_string_literal(source, start, quote=None):
    quote = start if quote is None else quote
    end = string_literal_end(source, quote + 1)
    data = bytearray()
    position = quote + 1
    while position < end:
        if source[position] == "\\":
            escaped = source[position + 1]
            value, position = read_escaped_char(source, position + 1)
            if escaped in "01234567x":
                data.append(value & 255)
            else:
                data.extend(chr(value).encode("utf-8"))
        else:
            data.extend(source[position].encode("utf-8"))
            position += 1
    data.append(0)
    token = Token("STR", source[start:end + 1], start,
                  ty=array_of(ty_char, len(data)), str=bytes(data))
    return token, end + 1


def read_utf16_string_literal(source, start, quote):
    end = string_literal_end(source, quote + 1)
    data = bytearray()
    position = quote + 1
    while position < end:
        if source[position] == "\\":
            value, position = read_escaped_char(source, position + 1)
            data.extend((value & 0xffff).to_bytes(2, 'little'))
        else:
            data.extend(source[position].encode('utf-16-le'))
            position += 1
    data.extend(b'\0\0')
    return Token('STR', source[start:end + 1], start,
                 ty=array_of(ty_ushort, len(data) // 2), str=bytes(data)), end + 1


def read_utf32_string_literal(source, start, quote, ty):
    end = string_literal_end(source, quote + 1)
    data = bytearray()
    position = quote + 1
    while position < end:
        if source[position] == "\\":
            value, position = read_escaped_char(source, position + 1)
        else:
            value = ord(source[position])
            position += 1
        data.extend((value & 0xffffffff).to_bytes(4, 'little'))
    data.extend(b'\0\0\0\0')
    return Token('STR', source[start:end + 1], start,
                 ty=array_of(ty, len(data) // 4), str=bytes(data)), end + 1


def tokenize_string_literal(token, basety):
    if basety.size == 2:
        converted, _ = read_utf16_string_literal(token.text, 0, 0)
    else:
        converted, _ = read_utf32_string_literal(token.text, 0, 0, basety)
    return converted


def read_char_literal(source, start, quote=None, ty=ty_int):
    position = (start if quote is None else quote) + 1
    if position >= len(source) or source[position] == "\0":
        raise CompileError(start, "unclosed char literal")
    if source[position] == "\\":
        if position + 1 >= len(source):
            raise CompileError(start, "unclosed char literal")
        value, position = read_escaped_char(source, position + 1)
    else:
        value = ord(source[position])
        position += 1
    end = source.find("'", position)
    if end == -1:
        raise CompileError(position, "unclosed char literal")
    return Token("NUM", source[start:end + 1], start, to_int32(value), ty=ty), end + 1


def read_int_literal(source, start, check_range=True):
    position = start
    base = 10
    alphanumeric = string.ascii_letters + string.digits
    prefix = source[start:start + 2].lower()
    if (start + 2 < len(source) and
            ((prefix == "0x" and source[start + 2] in string.hexdigits) or
             (prefix == "0b" and source[start + 2] in "01"))):
        base = 16 if prefix == "0x" else 2
        position += 2
    elif source[start] == "0":
        base = 8
    digits = string.hexdigits if base == 16 else string.digits[:base]
    first_digit = position
    while position < len(source) and source[position] in digits:
        position += 1
    try:
        value = int(source[first_digit:position], base)
    except ValueError:
        raise CompileError(start, "integer is too large to convert") from None
    if check_range and value > 2**64 - 1:
        raise CompileError(start, "integer must fit in unsigned 64 bits")
    is_long = is_unsigned = False
    suffix = source[position:]
    if suffix[:3] in ("LLU", "LLu", "llU", "llu", "ULL", "Ull", "uLL", "ull"):
        is_long = is_unsigned = True
        position += 3
    elif suffix[:2].lower() in ("lu", "ul"):
        is_long = is_unsigned = True
        position += 2
    elif suffix[:2] in ("LL", "ll"):
        is_long = True
        position += 2
    elif suffix[:1] in ("L", "l"):
        is_long = True
        position += 1
    elif suffix[:1] in ("U", "u"):
        is_unsigned = True
        position += 1
    if is_long and is_unsigned:
        ty = ty_ulong
    elif is_long:
        ty = ty_ulong if base != 10 and value >= 2**63 else ty_long
    elif is_unsigned:
        ty = ty_ulong if value >= 2**32 else ty_uint
    elif base == 10:
        ty = ty_long if value >= 2**31 else ty_int
    elif value >= 2**63:
        ty = ty_ulong
    elif value >= 2**32:
        ty = ty_long
    elif value >= 2**31:
        ty = ty_uint
    else:
        ty = ty_int
    if 2**63 <= value < 2**64:
        value -= 2**64
    return Token("NUM", source[start:position], start, value, ty=ty), position


def read_number(source, start):
    if source[start] != ".":
        token, position = read_int_literal(source, start, check_range=False)
        if position == len(source):
            if token.value >= 2**64:
                raise CompileError(start, "integer must fit in unsigned 64 bits")
            return token, position
    hexadecimal = source[start:start + 2].lower() == "0x"
    if hexadecimal:
        pattern = r"0[xX](?:[0-9a-fA-F]+(?:\.[0-9a-fA-F]*)?|\.[0-9a-fA-F]+)(?:[pP][+-]?[0-9]+)?"
    else:
        pattern = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    match = re.match(pattern, source[start:])
    if match is None:
        raise CompileError(start, "invalid numeric constant")
    spelling = match.group()
    try:
        value = float.fromhex(spelling) if hexadecimal else float(spelling)
    except OverflowError:
        value = float("inf")
    position = start + len(spelling)
    ty = ty_double
    if position < len(source) and source[position] in "fF":
        ty = ty_float
        position += 1
    elif position < len(source) and source[position] in "lL":
        position += 1
    if position != len(source):
        raise CompileError(start, "invalid numeric constant")
    return Token("NUM", source[start:position], start, ty=ty, fvalue=value), position


def add_line_numbers(source, tokens):
    line_no = 1
    position = 0
    for token in tokens:
        while position < token.position:
            if source[position] == "\n":
                line_no += 1
            position += 1
        token.line_no = line_no


def read_punct(source, position):
    operators = ("<<=", ">>=", "...", "==", "!=", "<=", ">=", "->", "+=", "-=",
                 "*=", "/=", "++", "--", "%=", "&=", "|=", "^=", "&&", "||", "<<", ">>", "##")
    for operator in operators:
        if source.startswith(operator, position):
            return operator
    return source[position] if source[position] in string.punctuation else None


def tokenize(source):
    tokens = []
    file = File("-", 1, source)
    position = 0
    at_bol = True
    has_space = False

    def append_token(token):
        nonlocal at_bol, has_space
        token.at_bol = at_bol
        token.file = file
        token.filename = file.display_name
        token.has_space = has_space
        at_bol = has_space = False
        tokens.append(token)

    while position < len(source):
        character = source[position]

        if source.startswith("//", position):
            end = source.find("\n", position + 2)
            position = len(source) if end == -1 else end
            has_space = True
            continue

        if source.startswith("/*", position):
            end = source.find("*/", position + 2)
            if end == -1:
                raise CompileError(position, "unclosed block comment")
            position = end + 2
            has_space = True
            continue

        if character == "\n":
            position += 1
            at_bol = True
            has_space = False
            continue

        if character.isspace():
            position += 1
            has_space = True
            continue

        if "0" <= character <= "9" or (character == "." and position + 1 < len(source) and "0" <= source[position + 1] <= "9"):
            start = position
            position += 1
            while position < len(source):
                if (source[position] in "eEpP" and position + 1 < len(source)
                        and source[position + 1] in "+-"):
                    position += 2
                elif source[position] in string.ascii_letters + string.digits + ".":
                    position += 1
                else:
                    break
            append_token(Token("PP_NUM", source[start:position], start))
            continue

        if character == '"':
            token, position = read_string_literal(source, position)
            append_token(token)
            continue
        if source.startswith('u8"', position):
            token, position = read_string_literal(source, position, position + 2)
            append_token(token)
            continue

        if source.startswith('u"', position):
            token, position = read_utf16_string_literal(source, position, position + 1)
            append_token(token)
            continue

        if source.startswith('U"', position):
            token, position = read_utf32_string_literal(source, position, position + 1, ty_uint)
            append_token(token)
            continue
        if source.startswith('L"', position):
            token, position = read_utf32_string_literal(source, position, position + 1, ty_int)
            append_token(token)
            continue

        if character == "'":
            token, position = read_char_literal(source, position)
            token.value = (token.value + 128) % 256 - 128
            append_token(token)
            continue

        if source.startswith("u'", position):
            token, position = read_char_literal(source, position, position + 1, ty_ushort)
            token.value &= 0xffff
            append_token(token)
            continue

        if source.startswith("L'", position):
            token, position = read_char_literal(source, position, position + 1)
            append_token(token)
            continue

        if source.startswith("U'", position):
            token, position = read_char_literal(source, position, position + 1, ty_uint)
            append_token(token)
            continue

        if is_ident1(character):
            start = position
            position += 1
            while position < len(source) and is_ident2(source[position]):
                position += 1
            append_token(Token("IDENT", source[start:position], start))
            continue

        operator = read_punct(source, position)
        if operator is not None:
            append_token(Token("PUNCT", operator, position))
            position += len(operator)
            continue

        raise CompileError(position, "invalid token")

    append_token(Token("EOF", "", position))
    add_line_numbers(source, tokens)
    return tokens


def convert_pp_tokens(tokens):
    for token in tokens:
        if token.text in ("return", "if", "else", "for", "while", "int", "sizeof", "char", "struct", "union", "short", "long", "void", "typedef", "_Bool", "enum", "static", "goto", "break", "continue", "switch", "case", "default", "extern", "_Alignof", "_Alignas", "do", "signed", "unsigned", "const", "volatile", "auto", "register", "restrict", "__restrict", "__restrict__", "_Noreturn", "float", "double", "typeof", "asm", "inline"):
            token.kind = "KEYWORD"
        elif token.kind == "PP_NUM":
            try:
                number, _ = read_number(token.text, 0)
            except CompileError as error:
                raise CompileError(token, str(error)) from None
            token.kind, token.value, token.ty, token.fvalue = (
                number.kind, number.value, number.ty, number.fvalue)
