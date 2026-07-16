# -*- coding: utf-8 -*-
"""앱 아이콘(192/512/apple-180/maskable-512) 생성 — 그라데이션 배경 + 이모지."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding="utf-8")

TOOLS = Path(__file__).resolve().parent
ICONS = TOOLS.parent / "assets" / "icons"
ICONS.mkdir(parents=True, exist_ok=True)

EMOJI = "🎫"
COLOR_TOP = (91, 79, 224)     # 인디고
COLOR_BOTTOM = (139, 124, 246)  # 바이올렛
FONT_PATH = r"C:\Windows\Fonts\seguiemj.ttf"


def rounded_gradient(size, radius_ratio=0.22):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (size, size))
    for y in range(size):
        t = y / (size - 1)
        r = int(COLOR_TOP[0] + (COLOR_BOTTOM[0] - COLOR_TOP[0]) * t)
        g = int(COLOR_TOP[1] + (COLOR_BOTTOM[1] - COLOR_TOP[1]) * t)
        b = int(COLOR_TOP[2] + (COLOR_BOTTOM[2] - COLOR_TOP[2]) * t)
        for x in range(size):
            grad.putpixel((x, y), (r, g, b, 255))
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * radius_ratio), fill=255)
    img.paste(grad, (0, 0), mask)
    return img


def add_emoji(img, size, emoji_ratio=0.56):
    d = ImageDraw.Draw(img)
    font_size = int(size * emoji_ratio)
    font = ImageFont.truetype(FONT_PATH, font_size)
    bbox = d.textbbox((0, 0), emoji, font=font, embedded_color=True) if False else None
    # textbbox may not report emoji glyph metrics reliably; use fixed centering offset
    x = size * 0.5 - font_size * 0.55
    y = size * 0.5 - font_size * 0.55
    d.text((x, y), emoji, font=font, embedded_color=True)
    return img


emoji = EMOJI

def build(size, out_name, square=False, maskable=False):
    if maskable:
        # 마스커블 아이콘: 안전 영역(가운데 80%)에만 콘텐츠, 배경은 꽉 채움
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        grad = rounded_gradient(size, radius_ratio=0)  # 사각형 풀블리드
        img.paste(grad, (0, 0), grad)
        add_emoji(img, size, emoji_ratio=0.42)
    elif square:
        img = rounded_gradient(size, radius_ratio=0.0)
        add_emoji(img, size)
    else:
        img = rounded_gradient(size, radius_ratio=0.22)
        add_emoji(img, size)
    img.save(ICONS / out_name)
    print("saved", out_name, img.size)


build(192, "app-icon-192.png")
build(512, "app-icon-512.png")
build(180, "app-icon-apple-180.png", square=True)  # 애플 터치 아이콘은 자체적으로 라운딩 처리
build(512, "app-icon-maskable-512.png", maskable=True)
