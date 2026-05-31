#!/usr/bin/env python3
"""
ig_text.py — genera immagini Instagram da testo con highlight.
Uso: python ig_text.py input.txt [--out DIR] [--format square|portrait|story]
Markup: *parola* → colore accent
"""

import sys
import re
import argparse
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── Palette ──────────────────────────────────────────────────────────────────
BG_COLOR      = "#0a0a0a"   # nero quasi puro
TEXT_COLOR    = "#e8e8e8"   # bianco caldo
ACCENT_COLOR  = "#00ff99"   # verde hacker
NUMBER_COLOR  = "#444444"   # grigio scuro per numerazione

# ── Formati Instagram (px) ────────────────────────────────────────────────────
FORMATS = {
    "square":  (1080, 1080),
    "portrait": (1080, 1350),
    "story":   (1080, 1920),
}

FONT_PATH = Path(__file__).parent / "fonts" / "ShareTechMono-Regular.ttf"

# ── Parse markup *parola* ─────────────────────────────────────────────────────
def parse_segments(text: str) -> list[tuple[str, bool]]:
    """Restituisce lista di (testo, is_accent). Normalizza newline in spazi."""
    text = re.sub(r'\n+', ' ', text)
    parts = re.split(r'(\*[^*]+\*)', text)
    segments = []
    for p in parts:
        if p.startswith('*') and p.endswith('*') and len(p) > 2:
            segments.append((p[1:-1].replace('\n', ' '), True))
        elif p:
            segments.append((p.replace('\n', ' '), False))
    return segments

# ── Word-wrap tenendo conto dei token ────────────────────────────────────────
def wrap_paragraph(para_segments, font, max_width, draw):
    """
    Avvolge i segmenti in righe che rispettano max_width.
    Ritorna lista di righe: ogni riga è lista di (word, is_accent).
    """
    # Esplodi in token (parola, is_accent)
    tokens = []
    for text, accent in para_segments:
        words = text.split(' ')
        for i, w in enumerate(words):
            if w:
                tokens.append((w, accent))
            if i < len(words) - 1:
                tokens.append((' ', accent))

    lines = []
    current = []
    current_w = 0
    space_w = draw.textlength(' ', font=font)

    for word, accent in tokens:
        if word == ' ':
            continue
        w = draw.textlength(word, font=font)
        gap = space_w if current else 0
        if current and current_w + gap + w > max_width:
            lines.append(current)
            current = [(word, accent)]
            current_w = w
        else:
            if current:
                current.append((' ', accent))
                current_w += space_w
            current.append((word, accent))
            current_w += w

    if current:
        lines.append(current)

    return lines

# ── Render riga con segmenti colorati ────────────────────────────────────────
def draw_line(draw, line_tokens, x_start, y, font):
    x = x_start
    for token, accent in line_tokens:
        color = ACCENT_COLOR if accent else TEXT_COLOR
        draw.text((x, y), token, font=font, fill=color)
        x += draw.textlength(token, font=font)

# ── Calcola font size ottimale ────────────────────────────────────────────────
def find_font_size(all_para_segments, canvas_w, canvas_h, padding, line_spacing_mult):
    usable_w = canvas_w - 2 * padding
    usable_h = canvas_h - 2 * padding

    for size in range(72, 18, -1):
        font = ImageFont.truetype(str(FONT_PATH), size)
        img_tmp  = Image.new("RGB", (canvas_w, canvas_h))
        draw_tmp = ImageDraw.Draw(img_tmp)
        line_h   = size * line_spacing_mult
        para_gap = size * 1.4

        total_h = 0
        for i, para in enumerate(all_para_segments):
            lines = wrap_paragraph(para, font, usable_w, draw_tmp)
            total_h += len(lines) * line_h
            if i < len(all_para_segments) - 1:
                total_h += para_gap

        if total_h <= usable_h:
            return font, size, line_h, para_gap

    font = ImageFont.truetype(str(FONT_PATH), 20)
    return font, 20, 20 * line_spacing_mult, 20 * 1.4

# ── Genera una singola immagine ───────────────────────────────────────────────
def render_image(all_para_segments, canvas_w, canvas_h,
                 padding, line_spacing_mult, label=None):

    font, size, line_h, para_gap = find_font_size(
        all_para_segments, canvas_w, canvas_h, padding, line_spacing_mult)

    img  = Image.new("RGB", (canvas_w, canvas_h), BG_COLOR)
    draw = ImageDraw.Draw(img)

    usable_w = canvas_w - 2 * padding

    # Calcola altezza totale per centratura verticale
    all_lines = []
    for para in all_para_segments:
        lines = wrap_paragraph(para, font, usable_w, draw)
        all_lines.append(lines)

    total_h = sum(len(ls) * line_h for ls in all_lines)
    total_h += para_gap * (len(all_lines) - 1)

    y = (canvas_h - total_h) / 2

    for p_idx, lines in enumerate(all_lines):
        for line in lines:
            draw_line(draw, line, padding, y, font)
            y += line_h
        if p_idx < len(all_lines) - 1:
            y += para_gap

    # Numerazione in basso a destra
    if label:
        num_font_size = max(16, size // 3)
        try:
            num_font = ImageFont.truetype(str(FONT_PATH), num_font_size)
        except Exception:
            num_font = font
        draw.text((canvas_w - padding, canvas_h - padding // 2),
                  label, font=num_font, fill=NUMBER_COLOR, anchor="rb")

    return img

# ── Split testo in chunk bilanciati ──────────────────────────────────────────
AVG_WORDS_THRESHOLD = 40  # sopra questa media → max 2 para/slide, altrimenti 3

def count_words(para_segments):
    return sum(len(t.split()) for t, _ in para_segments)

def split_into_chunks(paragraphs_segments, canvas_w, canvas_h,
                      padding, line_spacing_mult):
    """
    Distribuisce i paragrafi tra più slide con vincolo:
    - max 3 paragrafi/slide se media parole ≤ AVG_WORDS_THRESHOLD
    - max 2 paragrafi/slide altrimenti
    Bilancia evitando slide con peso molto diverso.
    """
    # Determina limite paragrafi per slide
    total_words = sum(count_words(p) for p in paragraphs_segments)
    avg_words   = total_words / len(paragraphs_segments) if paragraphs_segments else 0
    max_para    = 2 if avg_words > AVG_WORDS_THRESHOLD else 3

    usable_w = canvas_w - 2 * padding
    usable_h = canvas_h - 2 * padding * 1.1

    REF_SIZE     = 36
    ref_font     = ImageFont.truetype(str(FONT_PATH), REF_SIZE)
    img_tmp      = Image.new("RGB", (canvas_w, canvas_h))
    draw_tmp     = ImageDraw.Draw(img_tmp)
    ref_line_h   = REF_SIZE * line_spacing_mult
    ref_para_gap = REF_SIZE * 1.4

    def para_height(para):
        lines = wrap_paragraph(para, ref_font, usable_w, draw_tmp)
        return len(lines) * ref_line_h

    heights = [para_height(p) for p in paragraphs_segments]

    # Greedy con doppio vincolo: altezza canvas + max_para
    chunks    = []
    current   = []
    current_h = 0

    for i, para in enumerate(paragraphs_segments):
        h   = heights[i]
        gap = ref_para_gap if current else 0
        over_height = current and (current_h + gap + h > usable_h)
        over_count  = len(current) >= max_para

        if over_height or over_count:
            chunks.append(current)
            current   = [para]
            current_h = h
        else:
            current.append(para)
            current_h += gap + h

    if current:
        chunks.append(current)

    print(f"  [info] avg parole/para: {avg_words:.0f} → max {max_para} para/slide → {len(chunks)} slide")
    return chunks

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Genera immagini Instagram da testo.")
    parser.add_argument("input", help="File di testo sorgente")
    parser.add_argument("--out",    default="output", help="Directory di output (default: output)")
    parser.add_argument("--format", default="portrait",
                        choices=FORMATS.keys(), help="Formato Instagram (default: portrait)")
    parser.add_argument("--padding",  type=int, default=90,  help="Padding laterale px")
    parser.add_argument("--spacing",  type=float, default=1.7, help="Interlinea moltiplicatore")
    parser.add_argument("--prefix",   default="slide", help="Prefisso nome file output")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"Errore: file '{src}' non trovato.", file=sys.stderr)
        sys.exit(1)

    raw = src.read_text(encoding="utf-8").strip()
    # Paragrafi separati da riga vuota
    raw_paras = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
    paragraphs_segments = [parse_segments(p) for p in raw_paras]

    canvas_w, canvas_h = FORMATS[args.format]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    chunks = split_into_chunks(paragraphs_segments, canvas_w, canvas_h,
                               args.padding, args.spacing)

    n = len(chunks)
    for i, chunk in enumerate(chunks, 1):
        label = f"{i}/{n}" if n > 1 else None
        img   = render_image(chunk, canvas_w, canvas_h,
                             args.padding, args.spacing, label=label)
        out_path = out_dir / f"{args.prefix}-{i}.png"
        img.save(out_path, "PNG", optimize=True)
        print(f"  → {out_path}")

    print(f"\nDone: {n} immagine/i in '{out_dir}/'")

if __name__ == "__main__":
    main()
