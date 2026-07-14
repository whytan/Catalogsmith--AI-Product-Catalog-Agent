from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import (
    ConflictError,
    NotFoundError,
    SQLiteStorefrontAdapter,
    ValidationError as AdapterValidationError,
)
from agent.models.product import Product, ProductCreate, ProductFacts, ProductStatus, ProductUpdate

TOOL_NAMES = (
    "create_product",
    "update_product",
    "get_product",
    "list_products",
    "delete_product",
    "get_categories",
    "search_products",
    "publish",
    "unpublish",
)


class MCPToolError(Exception):
    """Raised when an MCP tool call fails."""


def _product_to_dict(product: Product) -> dict[str, Any]:
    return json.loads(product.model_dump_json())


def _facts_from_dict(data: dict[str, Any] | None) -> ProductFacts | dict[str, Any] | None:
    if data is None:
        return None
    return ProductFacts.model_validate(data)


async def dispatch_tool(
    session: AsyncSession,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    adapter = SQLiteStorefrontAdapter(session)

    try:
        if tool_name == "create_product":
            payload = ProductCreate(
                name=arguments["name"],
                price=arguments["price"],
                category=arguments["category"],
                description=arguments.get("description", ""),
                facts=_facts_from_dict(arguments.get("facts")),
                status=ProductStatus(arguments.get("status", ProductStatus.DRAFT.value)),
            )
            return _product_to_dict(await adapter.create_product(payload))

        if tool_name == "update_product":
            payload = ProductUpdate(
                name=arguments.get("name"),
                price=arguments.get("price"),
                category=arguments.get("category"),
                description=arguments.get("description"),
                facts=_facts_from_dict(arguments.get("facts")) if "facts" in arguments else None,
                status=ProductStatus(arguments["status"]) if arguments.get("status") else None,
            )
            return _product_to_dict(
                await adapter.update_product(int(arguments["product_id"]), payload)
            )

        if tool_name == "get_product":
            product = await adapter.get_product(int(arguments["product_id"]))
            if product is None:
                raise MCPToolError(f"Product {arguments['product_id']} not found.")
            return _product_to_dict(product)

        if tool_name == "list_products":
            products = await adapter.list_products(
                status=arguments.get("status"),
                category=arguments.get("category"),
            )
            return {"products": [_product_to_dict(product) for product in products], "total": len(products)}

        if tool_name == "delete_product":
            deleted = await adapter.delete_product(int(arguments["product_id"]))
            return {"deleted": deleted, "product_id": int(arguments["product_id"])}

        if tool_name == "get_categories":
            return {"categories": await adapter.get_categories()}

        if tool_name == "search_products":
            products = await adapter.search_products(
                arguments.get("query", ""),
                status=arguments.get("status"),
            )
            return {"products": [_product_to_dict(product) for product in products], "total": len(products)}

        if tool_name == "publish":
            return _product_to_dict(await adapter.publish(int(arguments["product_id"])))

        if tool_name == "unpublish":
            return _product_to_dict(await adapter.unpublish(int(arguments["product_id"])))

    except (ConflictError, NotFoundError, AdapterValidationError, ValueError) as exc:
        raise MCPToolError(str(exc)) from exc

    raise MCPToolError(f"Unknown tool: {tool_name}")
