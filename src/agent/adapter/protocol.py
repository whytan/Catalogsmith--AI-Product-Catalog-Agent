from typing import Protocol, runtime_checkable

from agent.models.product import Product, ProductCreate, ProductUpdate


class StorefrontAdapter(Protocol):
    """Nine-method catalog interface.

    All catalog writes flow through this boundary. Weekend 6 wraps it as an MCP server.
    A Shopify adapter would implement the same contract.
    """

    async def create_product(self, payload: ProductCreate) -> Product:
        """Insert a new product. Name must be unique."""
        ...

    async def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        """Partial update of an existing product."""
        ...

    async def get_product(self, product_id: int) -> Product | None:
        """Return one product by id, or None."""
        ...

    async def list_products(
        self,
        *,
        status: str | None = None,
        category: str | None = None,
    ) -> list[Product]:
        """List products, optionally filtered by status and/or category."""
        ...

    async def delete_product(self, product_id: int) -> bool:
        """Delete a product. Returns True if deleted."""
        ...

    async def get_categories(self) -> list[str]:
        """Return valid category names for this store."""
        ...

    async def search_products(self, query: str, *, status: str | None = None) -> list[Product]:
        """Case-insensitive search across name and description."""
        ...

    async def publish(self, product_id: int) -> Product:
        """Set status to published."""
        ...

    async def unpublish(self, product_id: int) -> Product:
        """Set status to draft."""
        ...
