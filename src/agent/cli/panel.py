from __future__ import annotations

import argparse
import asyncio

from agent.db.session import SessionLocal, init_db
from agent.personas.miner import mine_signal_clusters, propose_rewrite, question_frequency
from agent.personas.panel import run_persona_panel


async def _run_panel(limit: int) -> None:
    await init_db()
    async with SessionLocal() as session:
        result = await run_persona_panel(session, limit=limit)
    print(f"SYNTHETIC panel complete: {result['signals_created']} signals for {result['products']} products.")


async def _run_rewrite(product_id: int, theme: str) -> None:
    await init_db()
    async with SessionLocal() as session:
        before = await question_frequency(session, product_id=product_id, theme=theme)
        proposal = await propose_rewrite(session, product_id, theme)
        print("Rewrite proposal:")
        print(f"  product_id: {proposal['product_id']}")
        print(f"  theme: {proposal['theme']}")
        print(f"  reason: {proposal['reason']}")
        print(f"  proposed: {proposal['proposed_description'][:160]}...")
        print(f"  questions before: {before}")
        print("Approve via /app gate or API after starting rewrite session.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Catalogsmith SYNTHETIC persona panel")
    parser.add_argument("--limit", type=int, default=5, help="Published products to browse")
    parser.add_argument("--rewrite-product", type=int, default=None, help="Preview rewrite proposal")
    parser.add_argument("--theme", type=str, default="battery", help="Rewrite theme cluster")
    args = parser.parse_args()

    if args.rewrite_product:
        asyncio.run(_run_rewrite(args.rewrite_product, args.theme))
    else:
        asyncio.run(_run_panel(args.limit))


if __name__ == "__main__":
    main()
