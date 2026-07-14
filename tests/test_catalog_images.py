from agent.web.catalog_images import product_image_url


def test_product_image_url_resolves_jpg_stem():
    url = product_image_url("aurora-earbuds.jpg")
    assert url == "/static/products/aurora-earbuds.jpg"


def test_product_image_url_missing_file():
    assert product_image_url("not-a-real-product.jpg") is None


def test_product_image_url_empty():
    assert product_image_url("") is None
    assert product_image_url(None) is None
