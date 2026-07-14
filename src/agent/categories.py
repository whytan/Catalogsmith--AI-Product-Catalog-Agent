"""Valid product categories for the demo store."""

VALID_CATEGORIES: frozenset[str] = frozenset({"electronics", "kitchen", "beauty"})

CATEGORY_LABELS: dict[str, str] = {
    "electronics": "Electronics",
    "kitchen": "Kitchen",
    "beauty": "Beauty",
}

# CSS theme class per category (storefront product imagery)
CATEGORY_THEMES: dict[str, str] = {
    "electronics": "theme-electronics",
    "kitchen": "theme-kitchen",
    "beauty": "theme-beauty",
}
