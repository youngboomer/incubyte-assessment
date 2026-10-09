_FTS_STRIP = str.maketrans("", "", '"*:^()')


def sanitize_fts_query(query: str) -> str | None:
    """Turn free text into an FTS5 prefix query, or None when nothing remains."""
    tokens = [token for token in query.translate(_FTS_STRIP).split() if token]
    if not tokens:
        return None
    return " AND ".join(f"{token}*" for token in tokens)
