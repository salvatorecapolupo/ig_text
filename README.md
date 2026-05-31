# ig_text.py

CLI tool to generate Instagram-ready images from plain text files.

Write your content in a `.txt` file, mark emphasis words with `*asterisks*`,
and the script splits everything into balanced carousel slides automatically.

## Features

- **Auto carousel splitting** — long texts are distributed across multiple slides,
  each saved as `slide-1.png`, `slide-2.png`, etc., ready to upload as an
  Instagram carousel post
- **Smart balancing** — slide capacity adapts to average word count per paragraph:
  max 3 paragraphs/slide for short copy, max 2 for longer captions,
  so no slide looks overcrowded next to an almost-empty one
- **Inline highlights** — wrap any word or phrase in `*asterisks*` to render it
  in accent color; ideal for punchy hooks and key concepts
- **Auto font sizing** — text fills each slide at the largest readable size
  that fits, so every card looks intentional, not shrunken
- **Instagram formats** — outputs at native Instagram resolutions:
  `square` (1080×1080), `portrait` (1080×1350), `story` (1080×1920)
- **High-contrast aesthetic** — near-black background, off-white body text,
  bright green accent; designed for dark feed visibility

## Usage

```bash
python3 ig_text.py input.txt
python3 ig_text.py input.txt --format square
python3 ig_text.py input.txt --out ./my_carousel --prefix post
```

## Input format

Paragraphs separated by blank lines. Use `*word*` for highlighted text.
