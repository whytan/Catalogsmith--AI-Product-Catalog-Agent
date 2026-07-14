"""Generate product SVG illustrations for the demo catalog."""

from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "src" / "agent" / "web" / "static" / "products"
OUT.mkdir(parents=True, exist_ok=True)

PRODUCTS = [
    (
        "aurora-earbuds",
        "#5b7fc7",
        '<ellipse cx="200" cy="175" rx="95" ry="58" fill="#2a2a2a"/>'
        '<ellipse cx="130" cy="175" rx="22" ry="28" fill="#1a1a1a"/>'
        '<ellipse cx="270" cy="175" rx="22" ry="28" fill="#1a1a1a"/>'
        '<rect x="155" y="130" width="90" height="50" rx="12" fill="#3d3d3d"/>',
    ),
    (
        "pulse-band",
        "#5b7fc7",
        '<rect x="120" y="155" width="160" height="28" rx="14" fill="#1e2a3a"/>'
        '<rect x="175" y="120" width="50" height="98" rx="10" fill="#243447"/>'
        '<circle cx="200" cy="169" r="18" fill="#c45d26"/>',
    ),
    (
        "lumen-lamp",
        "#5b7fc7",
        '<rect x="185" y="200" width="30" height="55" fill="#6b6b6b"/>'
        '<ellipse cx="200" cy="120" rx="70" ry="25" fill="#f5f0e8"/>'
        '<path d="M170 145 Q200 90 230 145" stroke="#d4cdc3" stroke-width="8" fill="none"/>'
        '<ellipse cx="200" cy="145" rx="55" ry="18" fill="#fff8ee"/>',
    ),
    (
        "nova-speaker",
        "#5b7fc7",
        '<rect x="130" y="110" width="140" height="130" rx="22" fill="#2c3440"/>'
        '<circle cx="200" cy="175" r="42" fill="#1a1f28"/>'
        '<circle cx="200" cy="175" r="28" fill="#3a4450"/>'
        '<circle cx="200" cy="175" r="10" fill="#c45d26"/>',
    ),
    (
        "cedar-kettle",
        "#c49a6c",
        '<ellipse cx="200" cy="210" rx="75" ry="22" fill="#8b6914" opacity="0.3"/>'
        '<path d="M125 200 Q125 120 200 100 Q275 120 275 200 Z" fill="#b87333"/>'
        '<path d="M275 165 Q310 155 315 175 Q310 195 275 185" fill="#9a5c28"/>'
        '<rect x="188" y="88" width="24" height="18" rx="4" fill="#7a4a20"/>',
    ),
    (
        "bamboo-board",
        "#c49a6c",
        '<rect x="95" y="145" width="210" height="120" rx="8" fill="#d4a574"/>'
        '<rect x="95" y="145" width="210" height="12" rx="4" fill="#c49563"/>'
        '<ellipse cx="200" cy="205" rx="60" ry="8" fill="#b8895a" opacity="0.5"/>',
    ),
    (
        "mortar-pestle",
        "#c49a6c",
        '<ellipse cx="200" cy="220" rx="80" ry="25" fill="#6b6b6b" opacity="0.25"/>'
        '<path d="M130 210 Q130 150 200 140 Q270 150 270 210 Z" fill="#5a5a5a"/>'
        '<ellipse cx="200" cy="155" rx="55" ry="18" fill="#4a4a4a"/>'
        '<rect x="235" y="95" width="18" height="90" rx="9" fill="#6e6e6e" transform="rotate(25 244 140)"/>',
    ),
    (
        "copper-mugs",
        "#c49a6c",
        '<rect x="115" y="130" width="55" height="95" rx="6" fill="#b87333"/>'
        '<rect x="230" y="125" width="55" height="100" rx="6" fill="#cd7f32"/>'
        '<path d="M170 155 Q195 155 195 180 Q195 205 170 205" stroke="#8b5a2b" stroke-width="4" fill="none"/>'
        '<path d="M285 150 Q310 150 310 175 Q310 200 285 200" stroke="#8b5a2b" stroke-width="4" fill="none"/>',
    ),
    (
        "riverstone-serum",
        "#d4849a",
        '<rect x="175" y="110" width="50" height="130" rx="8" fill="#e8eef8" opacity="0.9"/>'
        '<rect x="180" y="120" width="40" height="90" rx="4" fill="#a8d4e8"/>'
        '<rect x="188" y="95" width="24" height="22" rx="4" fill="#c0c8d0"/>'
        '<ellipse cx="200" cy="230" rx="35" ry="8" fill="#9ab8c8" opacity="0.4"/>',
    ),
    (
        "meadow-mask",
        "#d4849a",
        '<rect x="155" y="130" width="90" height="140" rx="12" fill="#e8f0e4"/>'
        '<rect x="165" y="145" width="70" height="100" rx="8" fill="#c8dcc0"/>'
        '<rect x="188" y="115" width="24" height="22" rx="6" fill="#a8c0a0"/>',
    ),
    (
        "silk-mask",
        "#d4849a",
        '<path d="M120 175 Q200 120 280 175 Q200 230 120 175 Z" fill="#f0e6ef"/>'
        '<path d="M135 175 Q200 140 265 175 Q200 210 135 175 Z" fill="#e0d0dc"/>'
        '<rect x="85" y="168" width="30" height="14" rx="7" fill="#c8b8c4"/>'
        '<rect x="285" y="168" width="30" height="14" rx="7" fill="#c8b8c4"/>',
    ),
    (
        "citrus-scrub",
        "#d4849a",
        '<rect x="155" y="125" width="90" height="110" rx="10" fill="#f5e6d0"/>'
        '<ellipse cx="200" cy="125" rx="45" ry="10" fill="#e8d4b8"/>'
        '<circle cx="175" cy="175" r="12" fill="#f0a030" opacity="0.7"/>'
        '<circle cx="210" cy="190" r="10" fill="#e88c20" opacity="0.6"/>'
        '<circle cx="225" cy="160" r="8" fill="#f5b840" opacity="0.5"/>',
    ),
]


def svg(stem: str, accent: str, inner: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" role="img" aria-label="{stem}">
  <defs>
    <linearGradient id="bg-{stem}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#f7f5f2"/>
      <stop offset="100%" stop-color="#ece7df"/>
    </linearGradient>
  </defs>
  <rect width="400" height="300" fill="url(#bg-{stem})"/>
  <circle cx="320" cy="60" r="80" fill="{accent}" opacity="0.12"/>
  {inner}
</svg>"""


def main() -> None:
    for stem, accent, inner in PRODUCTS:
        (OUT / f"{stem}.svg").write_text(svg(stem, accent, inner), encoding="utf-8")
    print(f"Wrote {len(PRODUCTS)} product SVGs to {OUT}")


if __name__ == "__main__":
    main()
