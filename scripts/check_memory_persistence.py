"""Verify Chroma feedback survives a client reconnect (server-restart analogue).

Run with CHROMA_EPHEMERAL=0. Does not delete collections between write and read.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["CHROMA_EPHEMERAL"] = "0"
os.environ.setdefault("LLM_MOCK", "1")


def main() -> None:
    from agent.config import settings
    from agent.memory import store_feedback_in_memory
    from agent.memory import chroma as chroma_mod
    from agent.memory.feedback_store import retrieve_feedback_memories
    from agent.memory.voice_store import seed_voice_collection

    settings.chroma_ephemeral = False
    settings.llm_mock = True
    settings.memory_off = False

    marker = "PERSISTENCE_CHECK: no exclamation marks and avoid game-changer"
    store_feedback_in_memory(
        category="electronics",
        before="WOW!!! GAME-CHANGER draft",
        after="WOW!!! GAME-CHANGER draft",
        comment=marker,
        thread_id="persistence-check-1",
    )

    # Drop in-process client handle — simulate process restart without deleting files.
    chroma_mod._client = None

    seed_voice_collection()
    memories = retrieve_feedback_memories(
        category="electronics",
        query="earbuds battery electronics",
        limit=5,
    )
    joined = " ".join(memories)
    ok = (
        "PERSISTENCE_CHECK" in joined
        or "exclamation" in joined.lower()
        or "game-changer" in joined.lower()
    )
    print("chroma_ephemeral=", settings.chroma_ephemeral)
    print("retrieved=", memories)
    if ok:
        print("PASS: prior reject comment retrieved after client reconnect.")
        raise SystemExit(0)
    print("FAIL: prior reject comment not found after reconnect.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
