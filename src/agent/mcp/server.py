from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server.fastmcp import FastMCP

from agent.db.session import SessionLocal, init_db
from agent.mcp.tools import TOOL_NAMES, dispatch_tool


@asynccontextmanager
async def app_lifespan(_server: FastMCP) -> AsyncIterator[dict]:
    await init_db()
    yield {}


mcp = FastMCP(
    "catalogsmith-storefront",
    instructions=(
        "Catalogsmith storefront adapter exposed as MCP tools. "
        "All catalog writes must use these nine tools."
    ),
    lifespan=app_lifespan,
)


async def _call(tool_name: str, arguments: dict) -> dict:
    async with SessionLocal() as session:
        return await dispatch_tool(session, tool_name, arguments)


@mcp.tool(description="Create a new product draft. Name must be unique.")
async def create_product(
    name: str,
    price: str,
    category: str,
    description: str = "",
    status: str = "draft",
    facts: dict | None = None,
) -> dict:
    return await _call(
        "create_product",
        {
            "name": name,
            "price": price,
            "category": category,
            "description": description,
            "status": status,
            "facts": facts,
        },
    )


@mcp.tool(description="Partially update an existing product.")
async def update_product(
    product_id: int,
    name: str | None = None,
    price: str | None = None,
    category: str | None = None,
    description: str | None = None,
    status: str | None = None,
    facts: dict | None = None,
) -> dict:
    payload = {"product_id": product_id}
    if name is not None:
        payload["name"] = name
    if price is not None:
        payload["price"] = price
    if category is not None:
        payload["category"] = category
    if description is not None:
        payload["description"] = description
    if status is not None:
        payload["status"] = status
    if facts is not None:
        payload["facts"] = facts
    return await _call("update_product", payload)


@mcp.tool(description="Fetch one product by id.")
async def get_product(product_id: int) -> dict:
    return await _call("get_product", {"product_id": product_id})


@mcp.tool(description="List products, optionally filtered by status and category.")
async def list_products(status: str | None = None, category: str | None = None) -> dict:
    return await _call("list_products", {"status": status, "category": category})


@mcp.tool(description="Delete a product by id.")
async def delete_product(product_id: int) -> dict:
    return await _call("delete_product", {"product_id": product_id})


@mcp.tool(description="Return valid store categories.")
async def get_categories() -> dict:
    return await _call("get_categories", {})


@mcp.tool(description="Search products by name, description, or category.")
async def search_products(query: str, status: str | None = None) -> dict:
    return await _call("search_products", {"query": query, "status": status})


@mcp.tool(description="Publish a product to the storefront.")
async def publish(product_id: int) -> dict:
    return await _call("publish", {"product_id": product_id})


@mcp.tool(description="Move a published product back to draft.")
async def unpublish(product_id: int) -> dict:
    return await _call("unpublish", {"product_id": product_id})


def main() -> None:
    assert len(TOOL_NAMES) == 9
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
