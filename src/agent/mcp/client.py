from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.db.session import SessionLocal, init_db
from agent.mcp.tools import TOOL_NAMES, dispatch_tool


class StorefrontMCPClient:
    """MCP client for catalog writes.

    Default mode (`inline`) dispatches the same 9 tool contracts in-process.
    `stdio` mode is reserved for external MCP server processes (Claude Desktop).
    """

    def __init__(self, *, mode: str = "inline") -> None:
        self.mode = mode

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in TOOL_NAMES:
            raise ValueError(f"Unknown MCP tool: {tool_name}")

        if self.mode == "inline":
            async with SessionLocal() as session:
                return await dispatch_tool(session, tool_name, arguments)

        raise NotImplementedError(
            "stdio MCP transport is started via `catalogsmith-mcp`; "
            "use MCP_MODE=inline for the agent publish path."
        )

    async def create_and_publish(
        self,
        *,
        name: str,
        price: str,
        category: str,
        description: str,
        facts: dict[str, Any],
    ) -> dict[str, Any]:
        created = await self.call_tool(
            "create_product",
            {
                "name": name,
                "price": price,
                "category": category,
                "description": description,
                "facts": facts,
                "status": "draft",
            },
        )
        return await self.call_tool("publish", {"product_id": created["id"]})

    async def update_listing(self, *, product_id: int, description: str) -> dict[str, Any]:
        return await self.call_tool(
            "update_product",
            {"product_id": product_id, "description": description},
        )


def get_storefront_client() -> StorefrontMCPClient:
    from agent.config import settings

    return StorefrontMCPClient(mode=settings.mcp_mode)


async def ensure_db() -> None:
    await init_db()
