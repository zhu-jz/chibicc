"""The initial preprocessing stage only classifies keywords.

Based on chibicc commit 1e1ea39dadd0035443f1d15c651deaf979341879.
Original copyright (c) 2019 Rui Ueyama. See LICENSE.
"""

from tokenizer import convert_keywords


def preprocess(tokens):
    convert_keywords(tokens)
    return tokens
