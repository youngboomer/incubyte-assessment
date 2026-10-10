import re

_FTS_STRIP = str.maketrans("", "", '"*:^()')
_FTS_WORD = re.compile(r"\w+")
_FTS_OPERATORS = frozenset({"AND", "OR", "NOT", "NEAR"})


def sanitize_fts_query(query: str) -> str | None:
    """Turn free text into an FTS5 prefix query, or None when nothing remains.

    FTS5 barewords allow only word characters, so every other character
    separates tokens, as the unicode61 tokenizer does. Operator words are
    quoted so they match as text.
    """
    tokens = _FTS_WORD.findall(query.translate(_FTS_STRIP))
    if not tokens:
        return None
    return " AND ".join(
        f'"{token}"*' if token in _FTS_OPERATORS else f"{token}*" for token in tokens
    )
