from decimal import Decimal

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates

from agent.adapter.sqlite import AdapterError, ConflictError, NotFoundError, adapter_for
from agent.categories import CATEGORY_LABELS, CATEGORY_THEMES
from agent.config import settings
from agent.db.session import get_session
from agent.models.product import Product, ProductCreate, ProductListResponse, ProductStatus
from agent.web.jinja_helpers import register_template_globals

router = APIRouter(tags=["storefront"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "web" / "templates"
TEMPLATES = Jinja2Templates(directory=str(TEMPLATES_DIR))


def _format_inr(price: Decimal) -> str:
    return f"₹{price:,.2f}"


TEMPLATES.env.filters["inr"] = _format_inr
TEMPLATES.env.globals["store_name"] = settings.store_name
TEMPLATES.env.globals["category_labels"] = CATEGORY_LABELS
TEMPLATES.env.globals["category_themes"] = CATEGORY_THEMES
register_template_globals(TEMPLATES.env)


@router.get("/", response_class=HTMLResponse)
async def storefront_home(
    request: Request,
    q: str = Query(default=""),
    category: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    adapter = adapter_for(session)
    if q.strip():
        products = await adapter.search_products(q, status=ProductStatus.PUBLISHED.value)
    elif category:
        products = await adapter.list_products(
            status=ProductStatus.PUBLISHED.value,
            category=category,
        )
    else:
        products = await adapter.list_products(status=ProductStatus.PUBLISHED.value)

    categories = await adapter.get_categories()
    return TEMPLATES.TemplateResponse(
        request,
        "storefront/grid.html",
        {
            "products": products,
            "query": q,
            "active_category": category,
            "categories": categories,
            "total": len(products),
        },
    )


@router.get("/products/{product_id}", response_class=HTMLResponse)
async def storefront_product(
    request: Request,
    product_id: int,
    session: AsyncSession = Depends(get_session),
):
    adapter = adapter_for(session)
    product = await adapter.get_product(product_id)
    if product is None or product.status != ProductStatus.PUBLISHED:
        raise HTTPException(status_code=404, detail="Product not found")
    return TEMPLATES.TemplateResponse(
        request,
        "storefront/product.html",
        {"product": product},
    )


@router.get("/api/products", response_model=ProductListResponse)
async def api_list_products(
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> ProductListResponse:
    adapter = adapter_for(session)
    products = await adapter.list_products(status=status, category=category)
    return ProductListResponse(products=products, total=len(products))


@router.get("/api/products/{product_id}", response_model=Product)
async def api_get_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
) -> Product:
    adapter = adapter_for(session)
    product = await adapter.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/api/products", response_model=Product, status_code=201)
async def api_create_product(
    payload: ProductCreate,
    session: AsyncSession = Depends(get_session),
) -> Product:
    adapter = adapter_for(session)
    try:
        product = await adapter.create_product(payload)
        if payload.status == ProductStatus.PUBLISHED:
            product = await adapter.publish(product.id)
        return product
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except AdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/products/{product_id}/publish", response_model=Product)
async def api_publish_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
) -> Product:
    adapter = adapter_for(session)
    try:
        return await adapter.publish(product_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
