"""Dependency-free BM25 ranking for Chinese and ASCII text."""

import re
from collections import Counter
from collections.abc import Sequence
from math import log

_TOKEN_PATTERN = re.compile(r"[A-Za-z]+|\d+|[\u4e00-\u9fff]+")


def tokenize_chinese(text: str) -> list[str]:
    """Extract ASCII words, numbers, Chinese spans, and Chinese bigrams."""
    tokens: list[str] = []
    for match in _TOKEN_PATTERN.finditer(text):
        term = match.group()
        if "\u4e00" <= term[0] <= "\u9fff":
            tokens.append(term)
            tokens.extend(term[index : index + 2] for index in range(len(term) - 1))
        else:
            tokens.append(term.lower())
    return tokens


def bm25_rank(query: str, documents: Sequence[str]) -> list[int]:
    """Return document indexes ordered by descending BM25 relevance score."""
    if not documents:
        return []

    document_tokens = [tokenize_chinese(document) for document in documents]
    document_frequencies: Counter[str] = Counter()
    for tokens in document_tokens:
        document_frequencies.update(set(tokens))

    document_count = len(documents)
    average_length = sum(len(tokens) for tokens in document_tokens) / document_count or 1.0
    query_frequencies = Counter(tokenize_chinese(query))
    scores: list[float] = []

    for tokens in document_tokens:
        term_frequencies = Counter(tokens)
        length_normalizer = 1.5 * (1 - 0.75 + 0.75 * len(tokens) / average_length)
        score = 0.0
        for term, query_frequency in query_frequencies.items():
            frequency = term_frequencies[term]
            if not frequency:
                continue
            document_frequency = document_frequencies[term]
            inverse_document_frequency = log(
                1 + (document_count - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            score += query_frequency * inverse_document_frequency * (frequency * 2.5) / (
                frequency + length_normalizer
            )
        scores.append(score)

    return sorted(range(document_count), key=lambda index: scores[index], reverse=True)
