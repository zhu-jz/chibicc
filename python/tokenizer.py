"""Turn source characters into tokens.

Based on chibicc commit 1f9f3adf324af1432a380b41c7690834e649e346.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import string

from common import CompileError, Token


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

        if "a" <= character <= "z":
            tokens.append(Token("IDENT", character, position))
            position += 1
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
    return tokens
