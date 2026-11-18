"""Load portfolio SVG images when their section approaches the viewport."""
from pathlib import Path
import re

from PIL import Image

dist = Path(__file__).resolve().parent / 'dist'
path = dist / 'index.html'
source = path.read_text()
preloads = []


def defer_image(match):
    tag = match.group(0)
    resource = re.search(r'\s(?:xlink:href|href)="(assets/[^"#]+)"', tag)
    if not resource:
        return tag
    filename = resource[1]
    if 'data-cover-background' not in tag:
        return tag.replace(resource[0], f' data-lazy-href="{filename}"', 1)

    variants = []
    sizes = (
        ('small', 960, 85, '(max-width: 640px)'),
        ('medium', 1600, 88, '(640px < width <= 1100px)'),
        ('full', None, None, '(width > 1100px)'),
    )
    with Image.open(dist / filename) as original:
        for name, width, quality, media in sizes:
            variant = filename
            if width and original.width > width:
                variant = f'assets/{Path(filename).stem}-cover-{name}.webp'
                preview = original.copy()
                preview.thumbnail((width, original.height), Image.Resampling.LANCZOS)
                preview.save(dist / variant, 'WEBP', quality=quality, method=4)
            variants.append(f'data-cover-{name}="{variant}"')
            preloads.append(f'<link rel="preload" as="image" href="{variant}" fetchpriority="high" media="{media}">')
    return tag.replace(resource[0], ' ' + ' '.join(variants), 1)


def defer(match):
    return re.sub(r'<image\b[^>]*>', defer_image, match.group(0))


page = r'<section class="portfolio-page\b[^\"]*"[^>]*>.*?</section>'
source = re.sub(page, defer, source, flags=re.S)
source = source.replace('<!--COVER_PRELOAD-->', '\n  '.join(preloads))
source = source.replace('<img class="fence-background"',
                        '<img loading="lazy" width="15624" height="2064" class="fence-background"')
source = source.replace('<img src="assets/fence-strip.webp"', '<img loading="lazy" src="assets/fence-strip.webp"')
source = source.replace('<script src="app.js?v=2"></script>',
                        '<script src="art-corrections.js?v=14"></script><script src="lazy.js?v=15"></script><script src="app.js?v=17"></script>')
source = source.replace('style.css?v=2', 'style.css?v=16')
path.write_text(source)
