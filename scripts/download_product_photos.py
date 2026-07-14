"""Download realistic product photos into static/products/.

Sources: Unsplash (free to use, https://unsplash.com/license)
Re-run to refresh assets; deletes matching .svg stubs when a photo downloads.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "agent" / "web" / "static" / "products"

# stem must match seed photo_filename without extension
# Photos: Unsplash (free license) + generated fallbacks where URLs were unavailable
PRODUCT_PHOTOS: dict[str, str] = {
    "aurora-earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=900&h=675&fit=crop&q=85",
    "pulse-band": "",  # use scripts/generate_product_images.py or bundled asset
    "lumen-lamp": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=900&h=675&fit=crop&q=85",
    "nova-speaker": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=900&h=675&fit=crop&q=85",
    "cedar-kettle": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=900&h=675&fit=crop&q=85",
    "bamboo-board": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&w=900&q=85",
    "mortar-pestle": "",
    "copper-mugs": "",
    "riverstone-serum": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?auto=format&w=900&q=85",
    "meadow-mask": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=900&h=675&fit=crop&q=85",
    "silk-mask": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&w=900&q=85",
    "citrus-scrub": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?w=900&h=675&fit=crop&q=85",
}


def download(url: str, dest: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Catalogsmith/1.0 (demo catalog image fetch)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        dest.write_bytes(response.read())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = 0
    for stem, url in PRODUCT_PHOTOS.items():
        if not url.strip():
            print(f"SKIP {stem} (no URL — keep bundled .jpg)")
            continue
        dest = OUT / f"{stem}.jpg"
        try:
            download(url, dest)
            svg = OUT / f"{stem}.svg"
            if svg.is_file():
                svg.unlink()
            ok += 1
            print(f"OK  {stem}.jpg")
        except Exception as exc:
            print(f"FAIL {stem}: {exc}")
    print(f"Downloaded {ok}/{len(PRODUCT_PHOTOS)} photos to {OUT}")


if __name__ == "__main__":
    main()
