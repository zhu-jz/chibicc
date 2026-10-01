"""Turn source characters into tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import string
import re
import sys

from common import CompileError, Token
from type import array_of, ty_char, ty_int, ty_long, ty_uint, ty_ulong
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


def read_escaped_char(source, position):
    character = source[position]
    if "0" <= character <= "7":
        value = 0
        count = 0
        while position < len(source) and "0" <= source[position] <= "7" and count < 3:
            value = value * 8 + int(source[position])
            position += 1
            count += 1
        return bytes([value & 255]), position
    if character == "x":
        position += 1
        if position >= len(source) or source[position] not in string.hexdigits:
            raise CompileError(position, "invalid hex escape sequence")
        value = 0
        while position < len(source) and source[position] in string.hexdigits:
            value = value * 16 + int(source[position], 16)
            position += 1
        return bytes([value & 255]), position
    escapes = {"a": b"\a", "b": b"\b", "t": b"\t", "n": b"\n",
               "v": b"\v", "f": b"\f", "r": b"\r", "e": b"\x1b"}
    return escapes.get(character, character.encode("utf-8")), position + 1


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


def read_string_literal(source, start):
    end = string_literal_end(source, start + 1)
    data = bytearray()
    position = start + 1
    while position < end:
        if source[position] == "\\":
            value, position = read_escaped_char(source, position + 1)
            data.extend(value)
        else:
            data.extend(source[position].encode("utf-8"))
            position += 1
    data.append(0)
    token = Token("STR", source[start:end + 1], start,
                  ty=array_of(ty_char, len(data)), str=bytes(data))
    return token, end + 1


def read_char_literal(source, start):
    position = start + 1
    if position >= len(source) or source[position] == "\0":
        raise CompileError(start, "unclosed char literal")
    if source[position] == "\\":
        if position + 1 >= len(source):
            raise CompileError(start, "unclosed char literal")
        data, position = read_escaped_char(source, position + 1)
    else:
        data = source[position].encode("utf-8")
        position += 1
    end = source.find("'", position)
    if end == -1:
        raise CompileError(position, "unclosed char literal")
    value = data[0] if data[0] < 128 else data[0] - 256
    return Token("NUM", source[start:end + 1], start, value, ty=ty_int), end + 1


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
        if position == len(source) or source[position] not in ".eEfF":
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
        raise CompileError(start, "invalid floating literal")
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
    return Token("NUM", source[start:position], start, ty=ty, fvalue=value), position


def is_ident1(character):
    return "a" <= character <= "z" or "A" <= character <= "Z" or character == "_"


def is_ident2(character):
    return is_ident1(character) or "0" <= character <= "9"


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
                 "*=", "/=", "++", "--", "%=", "&=", "|=", "^=", "&&", "||", "<<", ">>")
    for operator in operators:
        if source.startswith(operator, position):
            return operator
    return source[position] if source[position] in string.punctuation else None


def tokenize(source):
    tokens = []
    position = 0

    while position < len(source):
        character = source[position]

        if source.startswith("//", position):
            end = source.find("\n", position + 2)
            position = len(source) if end == -1 else end
            continue

        if source.startswith("/*", position):
            end = source.find("*/", position + 2)
            if end == -1:
                raise CompileError(position, "unclosed block comment")
            position = end + 2
            continue

        if character.isspace():
            position += 1
            continue

        if "0" <= character <= "9" or (character == "." and position + 1 < len(source) and "0" <= source[position + 1] <= "9"):
            token, position = read_number(source, position)
            tokens.append(token)
            continue

        if character == '"':
            token, position = read_string_literal(source, position)
            tokens.append(token)
            continue

        if character == "'":
            token, position = read_char_literal(source, position)
            tokens.append(token)
            continue

        if is_ident1(character):
            start = position
            position += 1
            while position < len(source) and is_ident2(source[position]):
                position += 1
            tokens.append(Token("IDENT", source[start:position], start))
            continue

        operator = read_punct(source, position)
        if operator is not None:
            tokens.append(Token("PUNCT", operator, position))
            position += len(operator)
            continue

        raise CompileError(position, "invalid token")

    tokens.append(Token("EOF", "", position))
    add_line_numbers(source, tokens)
    for token in tokens:
        if token.text in ("return", "if", "else", "for", "while", "int", "sizeof", "char", "struct", "union", "short", "long", "void", "typedef", "_Bool", "enum", "static", "goto", "break", "continue", "switch", "case", "default", "extern", "_Alignof", "_Alignas", "do", "signed", "unsigned", "const", "volatile", "auto", "register", "restrict", "__restrict", "__restrict__", "_Noreturn"):
            token.kind = "KEYWORD"
    return tokens
