from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent / "review-batch"
SOURCE = ROOT / "_audit-frames"
OUTPUT = ROOT / "_audit-contact-sheets"
OUTPUT.mkdir(parents=True, exist_ok=True)

font = ImageFont.load_default(size=18)
for format_dir in sorted(p for p in SOURCE.iterdir() if p.is_dir()):
    files = sorted(format_dir.glob("*.jpg"))
    thumb_w, thumb_h = 320, 210
    label_h = 52
    cols = 4
    rows = (len(files) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "#07101d")
    draw = ImageDraw.Draw(sheet)
    for index, source in enumerate(files):
        image = Image.open(source).convert("RGB")
        image.thumbnail((thumb_w - 16, thumb_h - 16), Image.Resampling.LANCZOS)
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        px = x + (thumb_w - image.width) // 2
        py = y + (thumb_h - image.height) // 2
        sheet.paste(image, (px, py))
        label = source.stem.replace(f"-{format_dir.name}-", " · ")
        draw.text((x + 10, y + thumb_h + 6), label[:42], fill="#dbe7f5", font=font)
    sheet.save(OUTPUT / f"{format_dir.name}-audit-contact-sheet.jpg", quality=90)
