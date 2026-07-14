from __future__ import annotations

import hashlib
import math
import struct
from typing import cast

import chromadb
from chromadb import Collection
from chromadb.api import ClientAPI
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from agent.config import settings

VOICE_COLLECTION = "voice"
FEEDBACK_COLLECTION = "feedback"
EMBED_DIM = 64

_client: ClientAPI | None = None


class SimpleEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deterministic local embeddings — no model download required."""

    def __call__(self, input: Documents) -> Embeddings:
        return [embed_text(text) for text in input]

    def embed_documents(self, input: Documents) -> Embeddings:
        return self(input)

    def embed_query(self, input: Documents) -> Embeddings:
        return self(input)

    def name(self) -> str:
        return "simple-hash"


def embed_text(text: str, dim: int = EMBED_DIM) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for i in range(dim):
        start = (i * 4) % len(digest)
        chunk = digest[start : start + 4]
        if len(chunk) < 4:
            chunk = (chunk + digest)[:4]
        value = struct.unpack("!I", chunk)[0] / 2**32
        values.append(value)
    norm = math.sqrt(sum(v * v for v in values)) or 1.0
    return [v / norm for v in values]


def get_client() -> ClientAPI:
    global _client
    if _client is not None:
        return _client

    if settings.chroma_ephemeral:
        _client = chromadb.EphemeralClient()
    else:
        try:
            _client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            _client.heartbeat()
        except Exception:
            _client = chromadb.PersistentClient(path="data/chroma_local")

    return cast(ClientAPI, _client)


def get_collection(name: str) -> Collection:
    client = get_client()
    embedding = SimpleEmbeddingFunction()
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding,
    )


def reset_client() -> None:
    """Test helper — wipe collections and drop cached client.

    Chroma's EphemeralClient shares an in-process backend across instances,
    so setting _client = None alone does not isolate tests.
    """
    global _client
    client = _client
    if client is None and settings.chroma_ephemeral:
        client = chromadb.EphemeralClient()
    if client is not None:
        for name in (VOICE_COLLECTION, FEEDBACK_COLLECTION):
            try:
                client.delete_collection(name)
            except Exception:
                pass
    _client = None
