"""Run the learning ablation (memory ON vs OFF, deterministic rubric)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Learning ablation — rubric-gated drafts, memory ON vs OFF"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=ROOT / "data" / "ablation_report.json",
        help="JSON report path",
    )
    parser.add_argument(
        "--llm-mock",
        action="store_true",
        help="Use heuristic drafter (CI / offline). Omit for real Azure drafts.",
    )
    args = parser.parse_args()

    # Env must be set before Settings() is constructed by agent imports.
    if args.llm_mock:
        os.environ["LLM_MOCK"] = "1"
    else:
        os.environ["LLM_MOCK"] = "0"
    os.environ["CHROMA_EPHEMERAL"] = "0"

    asyncio.run(_run(args.output, args.llm_mock))


async def _run(output: Path, llm_mock: bool) -> None:
    from agent.config import settings
    from agent.db.session import SessionLocal, init_db
    from agent.memory.chroma import reset_client
    from eval.ablation import run_ablation, write_report

    settings.llm_mock = llm_mock
    settings.chroma_ephemeral = False

    await init_db()
    reset_client()

    async with SessionLocal() as session:
        report = await run_ablation(session, mode="mock" if llm_mock else "azure")

    write_report(report, output)
    print(json.dumps(report.to_dict(), indent=2))
    print(f"\nWrote {output}")
    print(
        f"mode={report.mode} claim={report.claim}\n"
        f"Mean edit rate  memory OFF: {report.memory_off.mean_edit_rate:.2f}  "
        f"ON: {report.memory_on.mean_edit_rate:.2f}  "
        f"delta: {report.delta_mean_edit_rate:+.2f}\n"
        f"N={report.n_products} improved={report.products_improved} "
        f"unchanged={report.products_unchanged} regressed={report.products_regressed}"
    )


if __name__ == "__main__":
    main()
