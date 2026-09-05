#!/usr/bin/env python3
"""Build Dagric's app icons and its three selectable icon families.

Third-party application marks are deliberately not redrawn.  Each Dagric
theme contains only Dagric-owned/iconless tool icons and inherits Breeze for
the rest, so an owner's choice changes our visual language without replacing
Firefox, Blender, LibreOffice, or another project's identity.
"""

import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "branding" / "icons" / "apps"
THEME_DIR = ROOT / "config" / "includes.chroot" / "usr" / "share" / "icons" / "hicolor"
ICONS_ROOT = THEME_DIR.parent
PREVIEW_DIR = (
    ROOT / "config" / "includes.chroot" / "usr" / "share" / "dagric"
    / "appearance" / "thumbs"
)
CONTACT_SHEET = ROOT / "branding" / "icons" / "dagric-app-icons-contact-sheet.png"
CONTACT_MANIFEST = CONTACT_SHEET.with_suffix(".json")
SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)
THEMES = {
    "modern": {
        "directory": "DagricModern",
        "name": "Dagric Modern",
        "comment": "Vivid dimensional icons with crisp silhouettes",
        "background": "#09111f",
    },
    "classic": {
        "directory": "DagricClassic",
        "name": "Dagric Classic",
        "comment": "Warm enamel badges inspired by durable desktop tools",
        "background": "#1a1713",
    },
    "old-school": {
        "directory": "DagricOldSchool",
        "name": "Dagric Old School",
        "comment": "Friendly pixel icons inspired by early personal computers",
        "background": "#17142b",
    },
}


def fitted(image: Image.Image, edge: int, fraction: float) -> Image.Image:
    target = max(1, round(edge * fraction))
    content = image.copy()
    content.thumbnail((target, target), Image.Resampling.LANCZOS)
    layer = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
    layer.alpha_composite(content, ((edge - content.width) // 2, (edge - content.height) // 2))
    return layer


def rounded_badge(edge: int, fill: tuple[int, int, int, int], outline: tuple[int, int, int, int],
                  inset: float = 0.055, radius: float = 0.22) -> Image.Image:
    badge = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    margin = round(edge * inset)
    width = max(2, round(edge * 0.022))
    draw.rounded_rectangle(
        (margin, margin, edge - margin - 1, edge - margin - 1),
        radius=round(edge * radius),
        fill=fill,
        outline=outline,
        width=width,
    )
    return badge


def make_variant(image: Image.Image, family: str) -> Image.Image:
    edge = image.width
    if family == "modern":
        return image.copy()

    if family == "classic":
        badge = rounded_badge(edge, (38, 32, 25, 242), (225, 180, 88, 255))
        inner = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
        draw = ImageDraw.Draw(inner)
        m = round(edge * 0.088)
        draw.rounded_rectangle(
            (m, m, edge - m - 1, edge - m - 1),
            radius=round(edge * 0.185),
            outline=(255, 236, 184, 165),
            width=max(1, round(edge * 0.008)),
        )
        content = fitted(image, edge, 0.77)
        content = ImageEnhance.Color(content).enhance(0.72)
        content = ImageEnhance.Contrast(content).enhance(1.08)
        shadow = content.getchannel("A").filter(ImageFilter.GaussianBlur(edge * 0.018))
        shadow_layer = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
        shadow_layer.putalpha(shadow.point(lambda p: round(p * 0.52)))
        badge.alpha_composite(shadow_layer, (round(edge * 0.012), round(edge * 0.018)))
        badge.alpha_composite(inner)
        badge.alpha_composite(content)
        return badge

    if family == "old-school":
        badge = rounded_badge(edge, (26, 22, 54, 246), (111, 226, 211, 255),
                              inset=0.045, radius=0.12)
        # Build the subject at a genuinely low resolution, then enlarge with
        # nearest-neighbour sampling.  This creates intentional pixels instead
        # of a fake pixel-art filter laid over smooth edges.
        low_edge = 64
        low = fitted(image.resize((low_edge, low_edge), Image.Resampling.LANCZOS),
                     low_edge, 0.78)
        alpha = low.getchannel("A")
        rgb = low.convert("RGB").quantize(colors=40, method=Image.Quantize.MEDIANCUT).convert("RGB")
        low = rgb.convert("RGBA")
        low.putalpha(alpha.point(lambda p: 255 if p >= 72 else 0))
        pixel = low.resize((edge, edge), Image.Resampling.NEAREST)
        shadow = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
        shadow_alpha = pixel.getchannel("A")
        shadow.putalpha(shadow_alpha.point(lambda p: 150 if p else 0))
        offset = max(2, round(edge * 0.025))
        badge.alpha_composite(shadow, (offset, offset))
        badge.alpha_composite(pixel)
        return badge

    raise ValueError(f"Unknown icon family: {family}")


def write_theme_metadata(theme_dir: Path, name: str, comment: str) -> None:
    directories = ",".join(f"{size}x{size}/apps" for size in SIZES)
    parts = [
        "[Icon Theme]",
        f"Name={name}",
        f"Comment={comment}",
        "Inherits=breeze-dark,breeze,hicolor",
        f"Directories={directories}",
        "",
    ]
    for size in SIZES:
        parts.extend([
            f"[{size}x{size}/apps]",
            f"Size={size}",
            "Context=Applications",
            "Type=Fixed",
            "",
        ])
    theme_dir.mkdir(parents=True, exist_ok=True)
    (theme_dir / "index.theme").write_text("\n".join(parts), encoding="utf-8", newline="\n")


def write_preview(family: str, variants: dict[str, Image.Image]) -> None:
    info = THEMES[family]
    canvas = Image.new("RGB", (480, 270), info["background"])
    draw = ImageDraw.Draw(canvas)
    chosen = (
        "dagric-hub", "dagric-appearance", "dagric-manual",
        "dagric-gaming", "dagric-migrate",
    )
    icon_edge = 78
    gap = 13
    total = icon_edge * len(chosen) + gap * (len(chosen) - 1)
    left = (canvas.width - total) // 2
    top = 81
    for index, name in enumerate(chosen):
        image = variants[name].resize((icon_edge, icon_edge), Image.Resampling.LANCZOS)
        canvas.paste(image, (left + index * (icon_edge + gap), top), image)
    title = info["name"].replace("Dagric ", "")
    draw.text((24, 22), title, fill="#f1f5fb", stroke_width=0)
    draw.text((24, 47), info["comment"], fill="#aab8ca", stroke_width=0)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    canvas.save(PREVIEW_DIR / f"icons-{family}.png", format="PNG", optimize=True)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_contact_sheet(images: dict[str, Image.Image]) -> None:
    """Render the review sheet and bind it to every source icon by hash."""
    columns, cell_width, cell_height, icon_edge = 6, 180, 150, 104
    rows = math.ceil(len(images) / columns)
    canvas = Image.new("RGB", (columns * cell_width, rows * cell_height), "#151a26")
    draw = ImageDraw.Draw(canvas)
    for index, (name, image) in enumerate(sorted(images.items())):
        column, row = index % columns, index // columns
        left = column * cell_width + (cell_width - icon_edge) // 2
        top = row * cell_height + 10
        thumb = image.resize((icon_edge, icon_edge), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (left, top), thumb)
        draw.text((column * cell_width + 7, row * cell_height + 121), name, fill="#e4eaf3")
    canvas.save(CONTACT_SHEET, format="PNG", optimize=True)
    source_hashes = {
        f"{name}-source.png": file_sha256(SOURCE_DIR / f"{name}-source.png")
        for name in sorted(images)
    }
    manifest = {
        "schemaVersion": 1,
        "generator": "tools/build-app-icons.py",
        "sources": source_hashes,
        "sheet": {
            "path": str(CONTACT_SHEET.relative_to(ROOT)).replace("\\", "/"),
            "sha256": file_sha256(CONTACT_SHEET),
            "width": canvas.width,
            "height": canvas.height,
        },
    }
    CONTACT_MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    sources = sorted(SOURCE_DIR.glob("*-source.png"))
    if not sources:
        raise SystemExit(f"No source icons found in {SOURCE_DIR}")

    full_variants: dict[str, dict[str, Image.Image]] = {family: {} for family in THEMES}
    source_images: dict[str, Image.Image] = {}
    for source in sources:
        icon_name = source.name.removesuffix("-source.png")
        with Image.open(source) as opened:
            image = opened.convert("RGBA")
            if image.getextrema()[3] == (255, 255):
                raise ValueError(f"Source icon has no transparency: {source}")

            if image.width != image.height:
                edge = max(image.size)
                square = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
                square.alpha_composite(
                    image,
                    ((edge - image.width) // 2, (edge - image.height) // 2),
                )
                image = square
            source_images[icon_name] = image.copy()

            for size in SIZES:
                destination_dir = THEME_DIR / f"{size}x{size}" / "apps"
                destination_dir.mkdir(parents=True, exist_ok=True)
                destination = destination_dir / f"{icon_name}.png"
                resized = image.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(destination, format="PNG", optimize=True)

            for family, info in THEMES.items():
                variant = make_variant(image, family)
                full_variants[family][icon_name] = variant
                theme_dir = ICONS_ROOT / info["directory"]
                for size in SIZES:
                    destination_dir = theme_dir / f"{size}x{size}" / "apps"
                    destination_dir.mkdir(parents=True, exist_ok=True)
                    destination = destination_dir / f"{icon_name}.png"
                    resized = variant.resize((size, size), Image.Resampling.LANCZOS)
                    resized.save(destination, format="PNG", optimize=True)

    for family, info in THEMES.items():
        write_theme_metadata(ICONS_ROOT / info["directory"], info["name"], info["comment"])
        write_preview(family, full_variants[family])
    write_contact_sheet(source_images)

    per_family = len(sources) * len(SIZES)
    print(
        f"Built {len(sources)} Dagric icons at {len(SIZES)} sizes in hicolor and "
        f"{len(THEMES)} selectable families ({per_family * (len(THEMES) + 1)} PNG files)."
    )


if __name__ == "__main__":
    main()
