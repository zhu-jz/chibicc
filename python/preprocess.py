"""Read quoted includes and remove null directives before keyword conversion.

Based on chibicc commit d367510fcc1396fa252c4b87439c2f9fcd0abbe7.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

import os
from dataclasses import replace

from tokenizer import convert_keywords, tokenize_file
from common import CompileError


def preprocess(tokens, files=None):
    if files is None:
        files = []
    result = []
    position = 0
    while tokens[position].kind != "EOF":
        token = tokens[position]
        if token.at_bol and token.text == "#":
            position += 1
            if tokens[position].text == "include":
                filename = tokens[position + 1]
                if filename.kind != "STR":
                    raise CompileError(filename, "expected a filename")
                including_file = filename.file.name if filename.file else "-"
                directory = os.path.dirname(including_file) or "."
                name = os.fsdecode(filename.str.split(b"\0", 1)[0])
                path = directory + "/" + name
                try:
                    included = tokenize_file(path, files)
                except CompileError as error:
                    if error.position is None:
                        raise CompileError(filename, str(error)) from None
                    raise
                tokens[position - 1:position + 2] = [replace(tok) for tok in included[:-1]]
                position -= 1
                continue
            if tokens[position].at_bol:
                continue
            raise CompileError(tokens[position], "invalid preprocessor directive")
        result.append(token)
        position += 1
    result.append(tokens[position])
    tokens[:] = result
    convert_keywords(tokens)
    return tokens
