import json
from functools import lru_cache
from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
METRIC_DICTIONARY_FILE = KNOWLEDGE_DIR / "metric_dictionary.json"


@lru_cache(maxsize=1)
def load_metric_dictionary():
    if not METRIC_DICTIONARY_FILE.exists():
        return []
    return json.loads(METRIC_DICTIONARY_FILE.read_text(encoding="utf-8"))


def normalize_text(value):
    return str(value or "").strip().lower()


def workspace_field_text(workspace_context):
    schema = (workspace_context or {}).get("schema") or {}
    fields = []
    for field in schema.get("fields") or []:
        if field.get("name"):
            fields.append(field["name"])
    fields.extend(schema.get("columns") or [])
    return " ".join(str(item) for item in fields)


def score_entry(entry, query_text, field_text):
    score = 0
    haystack = f"{query_text} {field_text}".lower()
    for keyword in entry.get("keywords") or []:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword and normalized_keyword in haystack:
            score += 3 if normalized_keyword in query_text else 1
    title = normalize_text(entry.get("title"))
    if title and title in haystack:
        score += 2
    return score


def search_knowledge(query, workspace_context=None, limit=3):
    query_text = normalize_text(query)
    field_text = normalize_text(workspace_field_text(workspace_context))
    matches = []
    for entry in load_metric_dictionary():
        score = score_entry(entry, query_text, field_text)
        if score <= 0:
            continue
        matches.append(
            {
                "title": entry.get("title"),
                "type": entry.get("type", "metric"),
                "summary": entry.get("summary", ""),
                "score": score,
            }
        )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return [{key: value for key, value in item.items() if key != "score"} for item in matches[:limit]]


def build_rag_catalog():
    entries = load_metric_dictionary()
    return {
        "enabled": True,
        "mode": "local_keyword_dictionary",
        "count": len(entries),
        "items": [
            {
                "title": entry.get("title"),
                "type": entry.get("type", "metric"),
                "summary": entry.get("summary", ""),
                "keywords": entry.get("keywords", [])[:5],
            }
            for entry in entries
        ],
    }
