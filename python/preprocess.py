"""Remove null directives before classifying keywords.

Based on chibicc commit 146c7b3dd47bb65da2da86cce7f4d75d8efa157d.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from tokenizer import convert_keywords
from common import CompileError


def preprocess(tokens):
    result = []
    position = 0
    while tokens[position].kind != "EOF":
        token = tokens[position]
        if token.at_bol and token.text == "#":
            position += 1
            if tokens[position].at_bol:
                continue
            raise CompileError(tokens[position], "invalid preprocessor directive")
        result.append(token)
        position += 1
    result.append(tokens[position])
    tokens[:] = result
    convert_keywords(tokens)
    return tokens
