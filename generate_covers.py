import os
import io
import django
import textwrap

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_system.settings")
django.setup()

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from books.models import Book

MEDIA_DIR = settings.MEDIA_ROOT
COVER_DIR = os.path.join(MEDIA_DIR, "book_covers")
os.makedirs(COVER_DIR, exist_ok=True)

COLOR_PALETTES = [
    ("#667eea", "#764ba2"), ("#f093fb", "#f5576c"), ("#4facfe", "#00f2fe"),
    ("#43e97b", "#38f9d7"), ("#fa709a", "#fee140"), ("#a18cd1", "#fbc2eb"),
    ("#fccb90", "#d57eeb"), ("#e0c3fc", "#8ec5fc"), ("#f5576c", "#ff6f00"),
    ("#667eea", "#00f2fe"), ("#ff0844", "#ffb199"), ("#b224ef", "#7579ff"),
    ("#0ba360", "#3cba92"), ("#ff9a9e", "#fecfef"), ("#a1c4fd", "#c2e9fb"),
]

WIDTH, HEIGHT = 500, 700

# try to find a CJK font
FONT_PATHS = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

font_path = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        font_path = fp
        break

if font_path is None:
    font_path = "/System/Library/Fonts/Helvetica.ttc"


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def create_gradient(width, height, color1_hex, color2_hex):
    base = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw_grad = ImageDraw.Draw(base)

    c1 = hex_to_rgb(color1_hex)
    c2 = hex_to_rgb(color2_hex)

    for y in range(height):
        ratio = y / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw_grad.line([(0, y), (width, y)], fill=(r, g, b, 255))

    return base


def create_decorative_pattern(draw, width, height):
    import math

    for i in range(0, width, 40):
        for j in range(0, height, 40):
            if (i // 40 + j // 40) % 2 == 0:
                draw.ellipse([i - 10, j - 10, i + 10, j + 10], fill=(255, 255, 255, 15))

    for k in range(5):
        x = width // 2 + int(180 * math.cos(k * 1.256))
        y = height // 3 + int(80 * math.sin(k * 1.256))
        draw.ellipse([x - 60, y - 60, x + 60, y + 60], outline=(255, 255, 255, 30), width=2)


def generate_cover(title, author, palette_idx):
    color1, color2 = COLOR_PALETTES[palette_idx % len(COLOR_PALETTES)]

    img = create_gradient(WIDTH, HEIGHT, color1, color2)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    create_decorative_pattern(overlay_draw, WIDTH, HEIGHT)

    overlay_draw.rectangle([35, 35, WIDTH - 35, HEIGHT - 35], outline=(255, 255, 255, 100), width=3)
    overlay_draw.rectangle([45, 45, WIDTH - 45, HEIGHT - 45], outline=(255, 255, 255, 50), width=1)

    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")

    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype(font_path, 48)
        font_author = ImageFont.truetype(font_path, 28)
        font_small = ImageFont.truetype(font_path, 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Title with text wrapping
    max_chars_per_line = 8
    wrapped_lines = []
    current_line = ""
    for char in title:
        if len(current_line.encode("utf-8")) < max_chars_per_line * 3:
            current_line += char
        else:
            wrapped_lines.append(current_line)
            current_line = char
    if current_line:
        wrapped_lines.append(current_line)

    if len(wrapped_lines) > 3:
        wrapped_lines = wrapped_lines[:3]
        wrapped_lines[-1] = wrapped_lines[-1][:-1] + "..."

    line_height = 58
    total_height = len(wrapped_lines) * line_height
    start_y = (HEIGHT // 2) - 60 - (total_height // 2)

    for i, line_text in enumerate(wrapped_lines):
        line_bbox = draw.textbbox((0, 0), line_text, font=font_title)
        line_width = line_bbox[2] - line_bbox[0]
        x = (WIDTH - line_width) // 2
        y = start_y + i * line_height

        # shadow
        draw.text((x + 3, y + 3), line_text, fill=(0, 0, 0, 60), font=font_title)
        draw.text((x, y), line_text, fill=(255, 255, 255), font=font_title)

    # Horizontal separator line
    sep_y = start_y + total_height + 30
    draw.line(
        [(WIDTH // 4, sep_y), (WIDTH * 3 // 4, sep_y)],
        fill=(255, 255, 255, 180),
        width=2,
    )

    # Author
    author_text = f"作者: {author}"
    author_bbox = draw.textbbox((0, 0), author_text, font=font_author)
    author_width = author_bbox[2] - author_bbox[0]
    draw.text(
        ((WIDTH - author_width) // 2, sep_y + 40),
        author_text,
        fill=(255, 255, 255, 220),
        font=font_author,
    )

    # Book icon at bottom
    icon_y = HEIGHT - 120
    icon_text = "📚 图书借阅管理系统"
    icon_bbox = draw.textbbox((0, 0), icon_text, font=font_small)
    icon_width = icon_bbox[2] - icon_bbox[0]
    draw.text(
        ((WIDTH - icon_width) // 2, icon_y),
        icon_text,
        fill=(255, 255, 255, 180),
        font=font_small,
    )

    return img


if __name__ == "__main__":
    print("=" * 50)
    print("图书封面生成器")
    print("=" * 50)

    books = Book.objects.filter(cover__isnull=True) | Book.objects.filter(cover="")
    count = 0

    for idx, book in enumerate(Book.objects.all()):
        print(f"[{idx+1}/{Book.objects.count()}] 生成: {book.title} ...", end=" ")

        img = generate_cover(book.title, book.author, idx)

        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG", quality=90)
        img_bytes.seek(0)

        filename = f"book_{book.id}_{book.isbn}.jpg"
        book.cover.save(filename, ContentFile(img_bytes.read()), save=True)

        print("✓")

    print("=" * 50)
    print(f"已为 {Book.objects.count()} 本图书生成封面!")
    print(f"封面目录: {COVER_DIR}")
    print("=" * 50)