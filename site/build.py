#!/usr/bin/env python3
"""Rebuild the static Sanzberro Collective site from site/src and the locked marks.

Writes HTML, CSS, and derived logo assets to the repository root, which is what
GitHub Pages serves. Does not touch CNAME, .nojekyll, or Pages settings.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SITE = Path(__file__).resolve().parent
SRC = SITE / "src"
BRAND = SITE / "brand"
BLACK_MASTER = BRAND / "sanzberro-logo-black-primary.jpg"
CREAM_MASTER = BRAND / "sanzberro-logo-cream.jpg"

BLACK = (0x1C, 0x1C, 0x1C)
CREAM = (0xF9, 0xF0, 0xE1)
IVORY = (0xF4, 0xF0, 0xE8)
INK = (0x0C, 0x0B, 0x0A)

BANNED = (
    "sandsboro",
    "vaults of plenty",
    "pyrenees",
    "central valley",
    "slogan factory",
    "mark-vault",
    "mark-seal",
    "ezpicbooth",
    "preview cannot",
    "greek treasury",
)


def wordmark_light(im: Image.Image) -> Image.Image:
    crop = im.crop((347, 390, 1073, 458))
    out = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    src = crop.load()
    dst = out.load()
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            lum = src[x, y][0]
            if lum <= 42:
                continue
            alpha = int(max(0, min(255, (lum - 42) * 255 / (190 - 42))))
            dst[x, y] = (*IVORY, alpha)
    return trim_alpha(out, pad=2)


def wordmark_dark(im: Image.Image) -> Image.Image:
    crop = im.crop((347, 392, 1074, 458))
    out = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    src = crop.load()
    dst = out.load()
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            lum = src[x, y][0]
            if lum >= 190:
                continue
            alpha = int(max(0, min(255, (190 - lum) * 255 / (190 - 40))))
            dst[x, y] = (*INK, alpha)
    return trim_alpha(out, pad=2)


def monogram_mask(im: Image.Image) -> Image.Image:
    crop = im.crop((470, 500, 980, 1064))
    mask = Image.new("L", crop.size, 0)
    src = crop.load()
    dst = mask.load()
    for y in range(crop.size[1]):
        for x in range(crop.size[0]):
            if src[x, y][0] < 120:
                dst[x, y] = 255
    mask = mask.filter(ImageFilter.MedianFilter(3))
    mask = mask.point(lambda v: 255 if v >= 96 else 0)
    bbox = mask.getbbox()
    if not bbox:
        raise SystemExit("monogram mask was empty")
    pad = 8
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(mask.size[0], bbox[2] + pad)
    y1 = min(mask.size[1], bbox[3] + pad)
    return mask.crop((x0, y0, x1, y1))


def trim_alpha(im: Image.Image, pad: int = 0) -> Image.Image:
    bbox = im.getbbox()
    if not bbox:
        return im
    x0 = max(0, bbox[0] - pad)
    y0 = max(0, bbox[1] - pad)
    x1 = min(im.size[0], bbox[2] + pad)
    y1 = min(im.size[1], bbox[3] + pad)
    return im.crop((x0, y0, x1, y1))


def paint(mask: Image.Image, color: tuple[int, int, int], blur: float = 0.45) -> Image.Image:
    soft = mask.filter(ImageFilter.GaussianBlur(blur)) if blur else mask
    out = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    src = soft.load()
    dst = out.load()
    for y in range(mask.size[1]):
        for x in range(mask.size[0]):
            alpha = src[x, y]
            if alpha:
                dst[x, y] = (*color, alpha)
    return out


def compose_lockup(word: Image.Image, mono: Image.Image, bg: tuple[int, int, int] | None) -> Image.Image:
    gap = max(28, int(word.size[1] * 1.15))
    width = max(word.size[0], mono.size[0]) + 48
    height = word.size[1] + gap + mono.size[1] + 48
    mode = "RGBA" if bg is None else "RGB"
    fill = (0, 0, 0, 0) if bg is None else bg
    canvas = Image.new(mode, (width, height), fill)
    canvas.paste(word, ((width - word.size[0]) // 2, 24), word)
    mono_y = 24 + word.size[1] + gap
    canvas.paste(mono, ((width - mono.size[0]) // 2, mono_y), mono)
    return canvas


def square_pad(mask: Image.Image, margin_ratio: float = 0.14) -> Image.Image:
    side = max(mask.size)
    margin = int(side * margin_ratio)
    canvas_side = side + margin * 2
    canvas = Image.new("L", (canvas_side, canvas_side), 0)
    canvas.paste(mask, ((canvas_side - mask.size[0]) // 2, (canvas_side - mask.size[1]) // 2))
    return canvas


def write_favicon_svg(mask: Image.Image, dest: Path) -> None:
    squared = square_pad(mask, 0.16)
    bw = ImageOps.invert(squared).convert("1")
    with tempfile.TemporaryDirectory() as tmp:
        pbm = Path(tmp) / "mono.pbm"
        raw = Path(tmp) / "mono.svg"
        bw.save(pbm)
        subprocess.check_call(
            [
                "potrace",
                "-s",
                "--flat",
                "--turdsize",
                "10",
                "--alphamax",
                "1.05",
                "--opttolerance",
                "0.25",
                "-o",
                str(raw),
                str(pbm),
            ]
        )
        traced = raw.read_text()
    start = traced.find("<g ")
    end = traced.rfind("</g>")
    if start < 0 or end < 0:
        raise SystemExit("potrace SVG had no path group")
    group = traced[start : end + 4].replace('fill="#000000"', 'fill="#f4f0e8"')
    width = squared.size[0]
    height = squared.size[1]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Sanzberro Collective">
  <rect width="{width}" height="{height}" fill="#1c1c1c"/>
  {group}
</svg>
"""
    dest.write_text(svg)


def favicon_png(mask: Image.Image, size: int) -> Image.Image:
    squared = square_pad(mask, 0.16)
    art = paint(squared, IVORY, blur=0.35)
    plate = Image.new("RGBA", squared.size, (*BLACK, 255))
    plate.alpha_composite(art)
    return plate.resize((size, size), Image.Resampling.LANCZOS).convert("RGB")


def render_pages(lockup_primary: Image.Image, lockup_cream: Image.Image) -> None:
    shell = (SRC / "shell.html").read_text()
    pages = {
        ROOT / "index.html": {
            "file": "home.html",
            "title": "Sanzberro Collective",
            "description": "Sanzberro Collective LLC is a family-owned company in Visalia, California. We sell what we make — directly, on marketplaces, and here.",
            "canonical": "https://sanzberrocollective.com/",
            "nav": "",
            "robots": "",
            "head": '<link rel="preload" as="image" href="/images/lockup-primary.png" />',
        },
        ROOT / "work" / "index.html": {
            "file": "work.html",
            "title": "Work · Sanzberro Collective",
            "description": "TruthLens, Benny, direct sales, and marketplace listings from Sanzberro Collective.",
            "canonical": "https://sanzberrocollective.com/work",
            "nav": "work",
            "robots": "",
            "head": "",
        },
        ROOT / "about" / "index.html": {
            "file": "about.html",
            "title": "About · Sanzberro Collective",
            "description": "Sanzberro Collective LLC is family-owned, formed in Visalia, California on August 19, 2026.",
            "canonical": "https://sanzberrocollective.com/about",
            "nav": "about",
            "robots": "",
            "head": "",
        },
        ROOT / "contact" / "index.html": {
            "file": "contact.html",
            "title": "Contact · Sanzberro Collective",
            "description": "Write Sanzberro Collective in Visalia, California. Sanzberrocollective@gmail.com.",
            "canonical": "https://sanzberrocollective.com/contact",
            "nav": "contact",
            "robots": "",
            "head": "",
        },
        ROOT / "404.html": {
            "file": "404.html",
            "title": "Not found · Sanzberro Collective",
            "description": "That page is not on the Sanzberro Collective site.",
            "canonical": "https://sanzberrocollective.com/404",
            "nav": "",
            "robots": '<meta name="robots" content="noindex" />',
            "head": "",
        },
    }
    current = 'aria-current="page"'
    for dest, meta in pages.items():
        body = (SRC / "pages" / meta["file"]).read_text()
        body = body.replace("{{LOCKUP_W}}", str(lockup_primary.size[0]))
        body = body.replace("{{LOCKUP_H}}", str(lockup_primary.size[1]))
        body = body.replace("{{CREAM_W}}", str(lockup_cream.size[0]))
        body = body.replace("{{CREAM_H}}", str(lockup_cream.size[1]))
        html = shell
        html = html.replace("{{TITLE}}", meta["title"])
        html = html.replace("{{DESCRIPTION}}", meta["description"])
        html = html.replace("{{CANONICAL}}", meta["canonical"])
        html = html.replace("{{ROBOTS}}", meta["robots"])
        html = html.replace("{{HEAD_EXTRA}}", meta["head"])
        html = html.replace("{{MAIN}}", body)
        for key in ("work", "about", "contact"):
            token = f"{{{{NAV_{key.upper()}}}}}"
            html = html.replace(token, current if meta["nav"] == key else "")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html)
        lowered = html.lower()
        for phrase in BANNED:
            if phrase in lowered:
                raise SystemExit(f"banned phrase {phrase!r} in {dest}")


def clean_retired() -> None:
    assets = ROOT / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    images = ROOT / "images"
    for name in (
        "atelier.jpg",
        "studio.jpg",
        "pyrenees.jpg",
        "pyrenees-quiet.jpg",
        "mark-seal.jpg",
        "mark-vault.jpg",
    ):
        path = images / name
        if path.exists():
            path.unlink()


def main() -> None:
    black = Image.open(BLACK_MASTER).convert("RGB")
    cream = Image.open(CREAM_MASTER).convert("RGB")
    light = wordmark_light(black)
    dark = wordmark_dark(cream)
    mask = monogram_mask(cream)
    mono_on_dark = paint(mask, (0x08, 0x08, 0x08), blur=0.55)
    mono_on_light = paint(mask, INK, blur=0.4)

    images = ROOT / "images"
    images.mkdir(exist_ok=True)
    shutil.copyfile(BLACK_MASTER, images / "logo-primary.jpg")
    shutil.copyfile(CREAM_MASTER, images / "logo-cream.jpg")
    light.save(images / "wordmark-light.png")
    dark.save(images / "wordmark-dark.png")

    lockup_primary = compose_lockup(light, mono_on_dark, BLACK)
    lockup_cream = compose_lockup(dark, mono_on_light, CREAM)
    lockup_primary.save(images / "lockup-primary.png", optimize=True)
    lockup_cream.save(images / "lockup-cream.png", optimize=True)

    og = Image.new("RGB", (1200, 630), BLACK)
    fitted = lockup_primary.copy()
    fitted.thumbnail((760, 560), Image.Resampling.LANCZOS)
    og.paste(fitted, ((1200 - fitted.size[0]) // 2, (630 - fitted.size[1]) // 2))
    og.save(ROOT / "og.jpg", quality=92, optimize=True)

    write_favicon_svg(mask, ROOT / "favicon.svg")
    icon32 = favicon_png(mask, 32)
    icon32.save(ROOT / "favicon.png", optimize=True)
    favicon_png(mask, 180).save(ROOT / "apple-touch-icon.png", optimize=True)
    favicon_png(mask, 256).save(
        ROOT / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48)],
    )

    shutil.copyfile(SRC / "style.css", ROOT / "style.css")
    render_pages(lockup_primary, lockup_cream)
    clean_retired()
    print("built", lockup_primary.size, lockup_cream.size, "wordmark", light.size)


if __name__ == "__main__":
    main()
