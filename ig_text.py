#!/usr/bin/env python3
"""
ig_text.py — genera immagini Instagram da testo con highlight.
Uso: python ig_text.py input.txt [--out DIR] [--format square|portrait|story]
Markup: *parola* → colore accent
Le prime due righe (paragrafi) del file = titolo e sottotitolo della slide 0.
"""

import sys
import re
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Palette ───────────────────────────────────────────────────────────────────
BG_COLOR      = "#0a0a0a"
TEXT_COLOR    = "#e8e8e8"
ACCENT_COLOR  = "#00ff99"
NUMBER_COLOR  = "#444444"

# ── Formati Instagram (px) ────────────────────────────────────────────────────
FORMATS = {
    "square":   (1080, 1080),
    "portrait": (1080, 1350),
    "story":    (1080, 1920),
}

FONT_PATH = Path(__file__).parent / "fonts" / "ShareTechMono-Regular.ttf"

# ── Split ─────────────────────────────────────────────────────────────────────
AVG_WORDS_THRESHOLD = 0  # 0 → sempre max_para=1 (cambia qui per aumentare)

def parse_segments(text):
    text = re.sub(r'\n+', ' ', text)
    parts = re.split(r'(\*[^*]+\*)', text)
    segments = []
    for p in parts:
        if p.startswith('*') and p.endswith('*') and len(p) > 2:
            segments.append((p[1:-1], True))
        elif p:
            segments.append((p, False))
    return segments

def wrap_paragraph(para_segments, font, max_width, draw):
    tokens = []
    for text, accent in para_segments:
        words = text.split(' ')
        for i, w in enumerate(words):
            if w:
                tokens.append((w, accent))
            if i < len(words) - 1:
                tokens.append((' ', accent))

    lines, current, current_w = [], [], 0
    space_w = draw.textlength(' ', font=font)

    for word, accent in tokens:
        if word == ' ':
            continue
        w = draw.textlength(word, font=font)
        gap = space_w if current else 0
        if current and current_w + gap + w > max_width:
            lines.append(current)
            current, current_w = [(word, accent)], w
        else:
            if current:
                current.append((' ', accent))
                current_w += space_w
            current.append((word, accent))
            current_w += w

    if current:
        lines.append(current)
    return lines

def draw_line(draw, line_tokens, x_start, y, font):
    x = x_start
    for token, accent in line_tokens:
        draw.text((x, y), token, font=font,
                  fill=ACCENT_COLOR if accent else TEXT_COLOR)
        x += draw.textlength(token, font=font)

def find_font_size(all_para_segments, canvas_w, canvas_h, padding, spacing):
    usable_w = canvas_w - 2 * padding
    usable_h = canvas_h - 2 * padding
    for size in range(72, 18, -1):
        font     = ImageFont.truetype(str(FONT_PATH), size)
        img_tmp  = Image.new("RGB", (canvas_w, canvas_h))
        draw_tmp = ImageDraw.Draw(img_tmp)
        line_h   = size * spacing
        para_gap = size * 1.4
        total_h  = 0
        for i, para in enumerate(all_para_segments):
            total_h += len(wrap_paragraph(para, font, usable_w, draw_tmp)) * line_h
            if i < len(all_para_segments) - 1:
                total_h += para_gap
        if total_h <= usable_h:
            return font, size, line_h, para_gap
    font = ImageFont.truetype(str(FONT_PATH), 20)
    return font, 20, 20 * spacing, 20 * 1.4

# ── Slide 0: titolo + sottotitolo ────────────────────────────────────────────
def render_cover(title, subtitle, canvas_w, canvas_h, padding, spacing):
    img  = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(img)
    usable_w = canvas_w - 2 * padding

    # Font sizes
    title_size    = 80
    subtitle_size = 42
    gap           = 60  # spazio tra titolo e sottotitolo

    title_font    = ImageFont.truetype(str(FONT_PATH), title_size)
    subtitle_font = ImageFont.truetype(str(FONT_PATH), subtitle_size)

    # Wrap titolo (testo puro, strip asterischi se presenti)
    title_clean = re.sub(r'\*', '', title)
    sub_clean   = re.sub(r'\*', '', subtitle)

    def wrap_text(text, font, max_w):
        words = text.split()
        lines, cur = [], []
        for w in words:
            test = ' '.join(cur + [w])
            if draw.textlength(test, font=font) <= max_w:
                cur.append(w)
            else:
                if cur:
                    lines.append(' '.join(cur))
                cur = [w]
        if cur:
            lines.append(' '.join(cur))
        return lines

    title_lines = wrap_text(title_clean, title_font, usable_w)
    sub_lines   = wrap_text(sub_clean,   subtitle_font, usable_w)

    title_h = len(title_lines) * title_size * spacing
    sub_h   = len(sub_lines)   * subtitle_size * spacing
    total_h = title_h + gap + sub_h

    y = (canvas_h - total_h) / 2

    # Disegna titolo centrato in ACCENT
    for line in title_lines:
        lw = draw.textlength(line, font=title_font)
        draw.text(((canvas_w - lw) / 2, y), line, font=title_font, fill=ACCENT_COLOR)
        y += title_size * spacing

    y += gap

    # Disegna sottotitolo centrato in TEXT
    for line in sub_lines:
        lw = draw.textlength(line, font=subtitle_font)
        draw.text(((canvas_w - lw) / 2, y), line, font=subtitle_font, fill=TEXT_COLOR)
        y += subtitle_size * spacing

    return img

# ── Slide normali ─────────────────────────────────────────────────────────────
def render_image(all_para_segments, canvas_w, canvas_h, padding, spacing, label=None):
    font, size, line_h, para_gap = find_font_size(
        all_para_segments, canvas_w, canvas_h, padding, spacing)

    img  = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(img)
    usable_w = canvas_w - 2 * padding

    all_lines = [wrap_paragraph(p, font, usable_w, draw) for p in all_para_segments]
    total_h   = sum(len(ls) * line_h for ls in all_lines)
    total_h  += para_gap * (len(all_lines) - 1)
    y = (canvas_h - total_h) / 2

    for p_idx, lines in enumerate(all_lines):
        for line in lines:
            draw_line(draw, line, padding, y, font)
            y += line_h
        if p_idx < len(all_lines) - 1:
            y += para_gap

    if label:
        num_size = max(16, size // 3)
        try:
            num_font = ImageFont.truetype(str(FONT_PATH), num_size)
        except Exception:
            num_font = font
        draw.text((canvas_w - padding, canvas_h - padding // 2),
                  label, font=num_font, fill=NUMBER_COLOR, anchor="rb")
    return img

# ── Split ─────────────────────────────────────────────────────────────────────
def count_words(para_segments):
    return sum(len(t.split()) for t, _ in para_segments)

def split_into_chunks(paragraphs_segments, canvas_w, canvas_h, padding, spacing):
    total_words = sum(count_words(p) for p in paragraphs_segments)
    avg_words   = total_words / len(paragraphs_segments) if paragraphs_segments else 0
    max_para    = 1  # ← cambia qui: 1, 2 o 3

    usable_w    = canvas_w - 2 * padding
    usable_h    = canvas_h - 2 * padding * 1.1
    REF_SIZE    = 36
    ref_font    = ImageFont.truetype(str(FONT_PATH), REF_SIZE)
    img_tmp     = Image.new("RGB", (canvas_w, canvas_h))
    draw_tmp    = ImageDraw.Draw(img_tmp)
    ref_line_h  = REF_SIZE * spacing
    ref_para_gap= REF_SIZE * 1.4

    def para_height(para):
        return len(wrap_paragraph(para, ref_font, usable_w, draw_tmp)) * ref_line_h

    heights = [para_height(p) for p in paragraphs_segments]
    chunks, current, current_h = [], [], 0

    for i, para in enumerate(paragraphs_segments):
        h   = heights[i]
        gap = ref_para_gap if current else 0
        if (current and current_h + gap + h > usable_h) or len(current) >= max_para:
            chunks.append(current)
            current, current_h = [para], h
        else:
            current.append(para)
            current_h += gap + h

    if current:
        chunks.append(current)

    print(f"  [info] avg parole/para: {avg_words:.0f} → max {max_para} para/slide → {len(chunks)} slide di contenuto")
    return chunks

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Genera immagini Instagram da testo.")
    parser.add_argument("input")
    parser.add_argument("--out",    default="output")
    parser.add_argument("--format", default="portrait", choices=FORMATS.keys())
    parser.add_argument("--padding",  type=int,   default=90)
    parser.add_argument("--spacing",  type=float, default=1.7)
    parser.add_argument("--prefix",   default="slide")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Errore: '{src}' non trovato.", file=sys.stderr)
        sys.exit(1)

    raw      = src.read_text(encoding="utf-8").strip()
    raw_paras = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]

    if len(raw_paras) < 2:
        print("Errore: servono almeno due paragrafi (titolo + sottotitolo).", file=sys.stderr)
        sys.exit(1)

    title    = raw_paras[0]
    subtitle = raw_paras[1]
    body     = raw_paras[2:]

    canvas_w, canvas_h = FORMATS[args.format]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Slide 0: cover
    cover = render_cover(title, subtitle, canvas_w, canvas_h, args.padding, args.spacing)
    cover_path = out_dir / f"{args.prefix}-0.png"
    cover.save(cover_path, "PNG", optimize=True)
    print(f"  → {cover_path}  [cover]")

    if not body:
        print("\nDone: solo cover generata.")
        return

    paragraphs_segments = [parse_segments(p) for p in body]
    chunks = split_into_chunks(paragraphs_segments, canvas_w, canvas_h,
                               args.padding, args.spacing)
    n = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        label    = f"{i}/{n}" if n > 1 else None
        img      = render_image(chunk, canvas_w, canvas_h,
                                args.padding, args.spacing, label=label)
        out_path = out_dir / f"{args.prefix}-{i}.png"
        img.save(out_path, "PNG", optimize=True)
        print(f"  → {out_path}")

    print(f"\nDone: 1 cover + {n} slide in '{out_dir}/'")

if __name__ == "__main__":
    main()
