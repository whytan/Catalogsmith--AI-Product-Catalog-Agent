from __future__ import annotations

from datetime import UTC, datetime

from agent.memory.chroma import VOICE_COLLECTION, get_collection
from agent.memory.voice import load_voice_rules


def seed_voice_collection() -> int:
    """Embed voice rules from YAML into Chroma if the collection is empty."""
    collection = get_collection(VOICE_COLLECTION)
    if collection.count() > 0:
        return 0

    rules = load_voice_rules()
    if not rules:
        return 0

    ids = [f"voice-{index}" for index in range(len(rules))]
    metadatas = [{"rule_id": f"rule-{index}", "source": "config"} for index in range(len(rules))]
    collection.add(ids=ids, documents=rules, metadatas=metadatas)
    return len(rules)


def retrieve_voice_rules(*, category: str, limit: int = 5) -> list[str]:
    collection = get_collection(VOICE_COLLECTION)
    if collection.count() == 0:
        return load_voice_rules()[:limit]

    query = f"store voice rules for {category} product descriptions"
    results = collection.query(query_texts=[query], n_results=min(limit, collection.count()))
    documents = results.get("documents", [[]])[0]
    return [doc for doc in documents if doc]
