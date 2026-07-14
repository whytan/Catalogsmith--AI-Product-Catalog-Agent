from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agent.categories import VALID_CATEGORIES


class ProductStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class ProductFacts(BaseModel):
    """Structured facts extracted from raw input (populated by parse node in Weekend 2)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = ""
    price: Decimal | None = None
    category: str = ""
    features: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    photo_filename: str = ""


class ProductCreate(BaseModel):
    """Input for creating a product via the adapter."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=200)]
    price: Annotated[Decimal, Field(gt=0, decimal_places=2, max_digits=12)]
    category: str
    description: str = ""
    facts: ProductFacts | dict[str, Any] | None = None
    status: ProductStatus = ProductStatus.DRAFT

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_CATEGORIES:
            allowed = ", ".join(sorted(VALID_CATEGORIES))
            raise ValueError(f"Invalid category '{value}'. Allowed: {allowed}")
        return normalized


class ProductUpdate(BaseModel):
    """Partial update for an existing product."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = None
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2, max_digits=12)
    category: str | None = None
    description: str | None = None
    facts: ProductFacts | dict[str, Any] | None = None
    status: ProductStatus | None = None

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in VALID_CATEGORIES:
            allowed = ", ".join(sorted(VALID_CATEGORIES))
            raise ValueError(f"Invalid category '{value}'. Allowed: {allowed}")
        return normalized


class Product(BaseModel):
    """A product record returned from the adapter."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    category: str
    description: str
    facts: ProductFacts
    status: ProductStatus
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    products: list[Product]
    total: int
