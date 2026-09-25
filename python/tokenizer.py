"""Turn source characters into tokens.

Based on chibicc commit 6cc1c1f0643ce0f1af0857e024a0a438ddb45853.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import string

from common import CompileError, Token


def is_ident1(character):
    return "a" <= character <= "z" or "A" <= character <= "Z" or character == "_"


def is_ident2(character):
    return is_ident1(character) or "0" <= character <= "9"


def tokenize(source):
    tokens = []
    position = 0

    while position < len(source):
        character = source[position]

        if character.isspace():
            position += 1
            continue

        if "0" <= character <= "9":
            start = position
            while position < len(source) and "0" <= source[position] <= "9":
                position += 1
            text = source[start:position]
            try:
                value = int(text, 10)
            except ValueError:
                raise CompileError(start, "integer is too large to convert") from None
            if value > 2**31 - 1:
                raise CompileError(start, "integer must fit in a signed 32-bit immediate")
            tokens.append(Token("NUM", text, start, value))
            continue

        if is_ident1(character):
            start = position
            position += 1
            while position < len(source) and is_ident2(source[position]):
                position += 1
            tokens.append(Token("IDENT", source[start:position], start))
            continue

        if source.startswith(("==", "!=", "<=", ">="), position):
            tokens.append(Token("PUNCT", source[position:position + 2], position))
            position += 2
            continue

        if character in string.punctuation:
            tokens.append(Token("PUNCT", character, position))
            position += 1
            continue

        raise CompileError(position, "invalid token")

    tokens.append(Token("EOF", "", position))
    for token in tokens:
        if token.text == "return":
            token.kind = "KEYWORD"
    return tokens
