from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import update

from agent.config import settings
from agent.db.schema import RunRow, utcnow
from agent.db.session import SessionLocal, init_db
from agent.llm.cost import total_cost_for_product
from agent.pipeline.nodes.draft import draft_node
from agent.pipeline.nodes.parse import parse_node
from agent.pipeline.nodes.publish import publish_node
from agent.pipeline.nodes.validate import validate_node


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add a product from raw facts: parse → draft → optional publish",
    )
    parser.add_argument("raw", help="Raw product facts in plain English")
    parser.add_argument("-y", "--yes", action="store_true", help="Publish without confirmation")
    parser.add_argument("--dry-run", action="store_true", help="Parse and draft only")
    return parser


def _print_block(title: str, body: str) -> None:
    print(f"\n--- {title} ---")
    print(body.encode("ascii", errors="replace").decode("ascii"))


async def _run(raw: str, *, auto_publish: bool, dry_run: bool) -> int:
    await init_db()
    async with SessionLocal() as session:
        started_at = utcnow()
        facts = await parse_node(raw, session)
        validated = await validate_node(facts, session)
        description = await draft_node(validated, session)

        _print_block(
            "Parsed facts",
            (
                f"Name:     {validated.name}\n"
                f"Price:    INR {validated.price:,.2f}\n"
                f"Category: {validated.category}\n"
                f"Features: {', '.join(validated.features) if validated.features else '—'}"
            ),
        )
        _print_block("Draft description", description)

        if settings.llm_mock:
            print("\n[mock mode] Set Azure keys in .env for live LLM calls.")

        if dry_run:
            return 0

        publish = auto_publish
        if not publish:
            answer = input("\nPublish to storefront? [y/N]: ").strip().lower()
            publish = answer in {"y", "yes"}

        if not publish:
            print("Not published.")
            return 0

        product = await publish_node(validated, description, session)
        await session.execute(
            update(RunRow)
            .where(RunRow.product_id.is_(None), RunRow.created_at >= started_at)
            .values(product_id=product.id)
        )
        await session.commit()
        cost = await total_cost_for_product(session, product.id)

        _print_block(
            "Published",
            (
                f"Product ID: {product.id}\n"
                f"Status:     {product.status}\n"
                f"Total cost: ${cost:.6f}\n"
                f"Storefront: /products/{product.id}"
            ),
        )
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.raw.strip():
        parser.error("Raw product text is required.")

    try:
        return asyncio.run(
            _run(args.raw, auto_publish=args.yes, dry_run=args.dry_run),
        )
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except Exception as exc:  # noqa: BLE001 — CLI top-level handler
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
