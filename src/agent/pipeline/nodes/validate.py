from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from agent.adapter.sqlite import ConflictError, SQLiteStorefrontAdapter
from agent.categories import VALID_CATEGORIES
from agent.models.product import ProductFacts


class ValidationIssue(BaseModel):
    field: str
    message: str


class ValidatedProduct(BaseModel):
    """Strict product facts after validation — ready for draft/publish."""

    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, decimal_places=2, max_digits=12)
    category: str
    features: list[str] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    photo_filename: str = ""

    @field_validator("category")
    @classmethod
    def category_must_be_valid(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in VALID_CATEGORIES:
            allowed = ", ".join(sorted(VALID_CATEGORIES))
            raise ValueError(f"Invalid category '{value}'. Allowed: {allowed}")
        return normalized


class ValidationResult(BaseModel):
    ok: bool
    product: ValidatedProduct | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)


def validate_facts_structural(facts: ProductFacts) -> ValidationResult:
    issues: list[ValidationIssue] = []

    if not facts.name.strip():
        issues.append(ValidationIssue(field="name", message="Product name is required."))
    if facts.price is None:
        issues.append(
            ValidationIssue(
                field="price",
                message="Selling price is required. Spec numbers like battery mAh are not prices — enter the retail price in INR.",
            )
        )
    elif facts.price <= 0:
        issues.append(ValidationIssue(field="price", message="Price must be greater than zero."))
    elif facts.price > Decimal("1000000"):
        issues.append(
            ValidationIssue(field="price", message="Price exceeds the allowed maximum (₹1,000,000).")
        )
    if not facts.category.strip():
        issues.append(ValidationIssue(field="category", message="Category is required."))
    elif facts.category.strip().lower() not in VALID_CATEGORIES:
        issues.append(
            ValidationIssue(
                field="category",
                message=f"Invalid category '{facts.category}'.",
            )
        )

    if issues:
        return ValidationResult(ok=False, issues=issues)

    try:
        product = ValidatedProduct(
            name=facts.name.strip(),
            price=facts.price,
            category=facts.category.strip().lower(),
            features=facts.features,
            ingredients=facts.ingredients,
            materials=facts.materials,
            photo_filename=facts.photo_filename,
        )
    except Exception as exc:  # noqa: BLE001 — collect pydantic message
        return ValidationResult(
            ok=False,
            issues=[ValidationIssue(field="product", message=str(exc))],
        )

    return ValidationResult(ok=True, product=product)


def apply_facts_completion(facts: ProductFacts, completion: dict[str, Any]) -> ProductFacts:
    """Merge seller-supplied fields after a needs_facts interrupt."""
    updates: dict[str, Any] = {}
    raw_price = completion.get("price")
    if raw_price is not None and str(raw_price).strip():
        cleaned = (
            str(raw_price)
            .lower()
            .replace("₹", "")
            .replace("inr", "")
            .replace("rs.", "")
            .replace("rs", "")
            .replace(",", "")
            .strip()
        )
        try:
            updates["price"] = Decimal(cleaned)
        except InvalidOperation:
            pass
    if completion.get("category"):
        updates["category"] = str(completion["category"]).strip().lower()
    if completion.get("name"):
        updates["name"] = str(completion["name"]).strip()
    if completion.get("photo_filename"):
        updates["photo_filename"] = str(completion["photo_filename"]).strip()
    if not updates:
        return facts
    return ProductFacts.model_validate({**facts.model_dump(mode="json"), **updates})


def format_validation_issues(issues: list[ValidationIssue], facts: ProductFacts) -> str:
    missing = ", ".join(issue.field for issue in issues)
    parsed_bits = []
    if facts.name.strip():
        parsed_bits.append(f"name: {facts.name.strip()}")
    if facts.category.strip():
        parsed_bits.append(f"category: {facts.category.strip()}")
    if facts.features:
        parsed_bits.append(f"{len(facts.features)} feature(s)")
    parsed = f" Parsed so far — {', '.join(parsed_bits)}." if parsed_bits else ""
    return (
        f"Missing required fields ({missing}). Add them in the panel on the right.{parsed}"
    )


async def validate_node(
    facts: ProductFacts,
    session: AsyncSession,
) -> ValidatedProduct:
    result = validate_facts_structural(facts)
    if not result.ok or result.product is None:
        messages = "; ".join(issue.message for issue in result.issues)
        raise ValueError(messages)

    adapter = SQLiteStorefrontAdapter(session)
    if await adapter.name_exists(result.product.name):
        raise ValueError(f"A product named '{result.product.name}' already exists.")

    return result.product
