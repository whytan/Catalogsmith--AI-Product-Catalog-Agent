"""CLI entrypoint for manual seeding."""

import asyncio

from agent.db.session import SessionLocal, init_db
from agent.seed import seed_if_empty


async def main() -> None:
    await init_db()
    async with SessionLocal() as session:
        count = await seed_if_empty(session)
        print(f"Seeded {count} products." if count else "Catalog already has products.")


if __name__ == "__main__":
    asyncio.run(main())
