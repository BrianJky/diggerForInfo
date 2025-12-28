from collections import Counter


def normalize_text(text: str) -> str:
    return (text or "").lower()


def contains_keywords(text: str, keywords: list[str]) -> bool:
    lowered = normalize_text(text)
    return any(keyword.lower() in lowered for keyword in keywords)


def apply_filters(
    title: str,
    content: str,
    tags: list[str],
    author: str,
    config: dict,
) -> tuple[bool, str, list[str]]:
    filtering = config.get("filtering", {})
    include_keywords = filtering.get("include_keywords", [])
    exclude_keywords = filtering.get("exclude_keywords", [])
    whitelist = filtering.get("author_whitelist", [])
    min_length = config.get("app", {}).get("min_content_length", 600)

    combined = " ".join([title or "", content or "", " ".join(tags or [])])

    if exclude_keywords and contains_keywords(combined, exclude_keywords):
        return False, "exclude_keyword", []

    if whitelist and author and author not in whitelist:
        return False, "author_not_whitelisted", []

    matched = [kw for kw in include_keywords if kw.lower() in combined.lower()]
    if include_keywords and not matched:
        return False, "no_include_keyword", []

    if len(content or "") < min_length:
        return False, "content_too_short", []

    return True, "ok", matched


def keyword_stats(records: list[dict]) -> dict:
    counter = Counter()
    for record in records:
        for keyword in record.get("matched_keywords", []):
            counter[keyword] += 1
    return dict(counter.most_common())
