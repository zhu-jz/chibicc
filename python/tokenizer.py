"""Turn source characters into tokens.

Based on chibicc commit b4e82cf7ce1cbfff8dd30f20fdad73fd3f1d5ccb.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import string
import sys

from common import CompileError, Token
from type import array_of, ty_char


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
    return Token("NUM", source[start:end + 1], start, value), end + 1


def read_int_literal(source, start):
    position = start
    base = 10
    alphanumeric = string.ascii_letters + string.digits
    if (source[start:start + 2].lower() in ("0x", "0b")
            and start + 2 < len(source) and source[start + 2] in alphanumeric):
        base = 16 if source[start + 1].lower() == "x" else 2
        position += 2
    elif source[start] == "0":
        base = 8
    digits = string.hexdigits if base == 16 else string.digits[:base]
    first_digit = position
    while position < len(source) and source[position] in digits:
        position += 1
    if position < len(source) and source[position] in alphanumeric:
        raise CompileError(position, "invalid digit")
    try:
        value = int(source[first_digit:position], base)
    except ValueError:
        raise CompileError(start, "integer is too large to convert") from None
    if value > 2**63 - 1:
        raise CompileError(start, "integer must fit in a signed 64-bit immediate")
    return Token("NUM", source[start:position], start, value), position


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

        if "0" <= character <= "9":
            token, position = read_int_literal(source, position)
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

        if source.startswith(("==", "!=", "<=", ">=", "->", "+=", "-=", "*=", "/=", "++", "--", "%="), position):
            tokens.append(Token("PUNCT", source[position:position + 2], position))
            position += 2
            continue

        if character in string.punctuation:
            tokens.append(Token("PUNCT", character, position))
            position += 1
            continue

        raise CompileError(position, "invalid token")

    tokens.append(Token("EOF", "", position))
    add_line_numbers(source, tokens)
    for token in tokens:
        if token.text in ("return", "if", "else", "for", "while", "int", "sizeof", "char", "struct", "union", "short", "long", "void", "typedef", "_Bool", "enum", "static"):
            token.kind = "KEYWORD"
    return tokens
