from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.protocol import StorefrontAdapter
from agent.categories import VALID_CATEGORIES
from agent.db.schema import ProductRow, dumps_json, loads_json, utcnow
from agent.models.product import Product, ProductCreate, ProductFacts, ProductStatus, ProductUpdate


class AdapterError(Exception):
    """Base adapter error."""


class NotFoundError(AdapterError):
    pass


class ConflictError(AdapterError):
    pass


class ValidationError(AdapterError):
    pass


def _row_to_product(row: ProductRow) -> Product:
    facts_data = loads_json(row.facts_json)
    return Product(
        id=row.id,
        name=row.name,
        price=row.price,
        category=row.category,
        description=row.description,
        facts=ProductFacts.model_validate(facts_data),
        status=ProductStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _facts_to_json(facts: ProductFacts | dict[str, Any] | None, payload: ProductCreate) -> str:
    if facts is None:
        data = ProductFacts(
            name=payload.name,
            price=payload.price,
            category=payload.category,
            features=[],
            ingredients=[],
            materials=[],
            photo_filename="",
        )
    elif isinstance(facts, ProductFacts):
        data = facts
    else:
        data = ProductFacts.model_validate(facts)
    return dumps_json(data.model_dump(mode="json"))


class SQLiteStorefrontAdapter:
    """SQLite implementation of the nine-method storefront adapter."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_product(self, payload: ProductCreate) -> Product:
        existing = await self._session.execute(
            select(ProductRow).where(ProductRow.name == payload.name)
        )
        if existing.scalar_one_or_none() is not None:
            raise ConflictError(f"A product named '{payload.name}' already exists.")

        now = utcnow()
        row = ProductRow(
            name=payload.name,
            price=payload.price,
            category=payload.category,
            description=payload.description,
            facts_json=_facts_to_json(payload.facts, payload),
            status=payload.status.value,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_product(row)

    async def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        row = await self._get_row(product_id)

        if payload.name is not None and payload.name != row.name:
            existing = await self._session.execute(
                select(ProductRow).where(ProductRow.name == payload.name)
            )
            if existing.scalar_one_or_none() is not None:
                raise ConflictError(f"A product named '{payload.name}' already exists.")
            row.name = payload.name

        if payload.price is not None:
            row.price = payload.price
        if payload.category is not None:
            row.category = payload.category
        if payload.description is not None:
            row.description = payload.description
        if payload.facts is not None:
            if isinstance(payload.facts, ProductFacts):
                row.facts_json = dumps_json(payload.facts.model_dump(mode="json"))
            else:
                row.facts_json = dumps_json(payload.facts)
        if payload.status is not None:
            row.status = payload.status.value

        row.updated_at = utcnow()
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_product(row)

    async def get_product(self, product_id: int) -> Product | None:
        row = await self._get_row_or_none(product_id)
        return _row_to_product(row) if row else None

    async def list_products(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
    ) -> list[Product]:
        stmt = select(ProductRow).order_by(ProductRow.created_at.desc())
        if status is not None:
            stmt = stmt.where(ProductRow.status == status)
        if category is not None:
            stmt = stmt.where(ProductRow.category == category.lower())
        result = await self._session.execute(stmt)
        return [_row_to_product(row) for row in result.scalars().all()]

    async def delete_product(self, product_id: int) -> bool:
        row = await self._get_row_or_none(product_id)
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def get_categories(self) -> list[str]:
        return sorted(VALID_CATEGORIES)

    async def name_exists(self, name: str) -> bool:
        result = await self._session.execute(
            select(ProductRow.id).where(ProductRow.name == name)
        )
        return result.scalar_one_or_none() is not None

    async def search_products(self, query: str, *, status: str | None = None) -> list[Product]:
        q = query.strip().lower()
        if not q:
            return await self.list_products(status=status)

        pattern = f"%{q}%"
        stmt = select(ProductRow).where(
            or_(
                ProductRow.name.ilike(pattern),
                ProductRow.description.ilike(pattern),
                ProductRow.category.ilike(pattern),
            )
        )
        if status is not None:
            stmt = stmt.where(ProductRow.status == status)
        stmt = stmt.order_by(ProductRow.created_at.desc())
        result = await self._session.execute(stmt)
        return [_row_to_product(row) for row in result.scalars().all()]

    async def publish(self, product_id: int) -> Product:
        row = await self._get_row(product_id)
        row.status = ProductStatus.PUBLISHED.value
        row.updated_at = utcnow()
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_product(row)

    async def unpublish(self, product_id: int) -> Product:
        row = await self._get_row(product_id)
        row.status = ProductStatus.DRAFT.value
        row.updated_at = utcnow()
        await self._session.commit()
        await self._session.refresh(row)
        return _row_to_product(row)

    async def _get_row(self, product_id: int) -> ProductRow:
        row = await self._get_row_or_none(product_id)
        if row is None:
            raise NotFoundError(f"Product {product_id} not found.")
        return row

    async def _get_row_or_none(self, product_id: int) -> ProductRow | None:
        result = await self._session.execute(select(ProductRow).where(ProductRow.id == product_id))
        return result.scalar_one_or_none()


def adapter_for(session: AsyncSession) -> StorefrontAdapter:
    return SQLiteStorefrontAdapter(session)
