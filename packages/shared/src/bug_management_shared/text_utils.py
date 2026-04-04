import re
from typing import Iterable, List


TOKEN_SPLIT_RE = re.compile(r"[\s,_\-]+")
SPARK_KEYWORDS = ("select", "withColumn", "drop", "alias", "join", "filter")


def normalize_key(value: str) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_issue_text(value: str) -> str:
    return normalize_spaces(value)


def dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    output = []
    for item in items:
        lowered = item.lower()
        if lowered in seen or not item:
            continue
        seen.add(lowered)
        output.append(item)
    return output


def extract_candidate_columns(text: str) -> List[str]:
    candidates = []
    lowered = text.lower()
    explicit_patterns = [
        r"(?:column|col)\s+`?([a-zA-Z][a-zA-Z0-9_]*)`?",
        r"`([a-zA-Z][a-zA-Z0-9_]*)`",
    ]
    for pattern in explicit_patterns:
        candidates.extend(re.findall(pattern, lowered))

    for token in TOKEN_SPLIT_RE.split(lowered):
        if (
            "_" in token
            and len(token) > 3
            and token not in {"column", "missing", "issue", "table", "value"}
        ):
            candidates.append(token)
    return dedupe(candidates)
