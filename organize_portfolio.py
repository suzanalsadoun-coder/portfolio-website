"""Move social projects into their own pages and insert the framed variety video."""
from copy import deepcopy
from functools import lru_cache
from html import escape
import json
from pathlib import Path
import re

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from lxml import etree
from PIL import Image

DIST = Path(__file__).resolve().parent / 'dist'
INDEX = DIST / 'index.html'
SVG = 'http://www.w3.org/2000/svg'
XLINK = '{http://www.w3.org/1999/xlink}href'
SVG_TAG = f'{{{SVG}}}'
URL_REFERENCE = re.compile(r'url\(#([^)]*)\)')
GALLERY_SCRIPT = re.compile(r'(<script id="gallery-data" type="application/json">)(.*?)(</script>)', re.S)
NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def read_svg(section):
    return etree.fromstring(section[section.index('<svg'):section.rindex('</svg>') + 6].encode(),
                            etree.XMLParser(huge_tree=True))


def svg_references(nodes):
    for node in nodes:
        for name, value in node.attrib.items():
            if name in ('href', XLINK) and value.startswith('#'):
                yield value[1:]
            yield from URL_REFERENCE.findall(value)


def svg_bounds(svg):
    by_id = {node.get('id'): node for node in svg.iter() if node.get('id')}

    @lru_cache(maxsize=None)
    def bounds(node):
        if node.get('data-bounds'):
            return tuple(json.loads(node.get('data-bounds')))

        tag = etree.QName(node).localname
        matrix = re.findall(NUMBER, node.get('transform', ''))
        transform = tuple(map(float, matrix)) if len(matrix) == 6 else (1, 0, 0, 1, 0, 0)
        if tag == 'path':
            pen = BoundsPen(None)
            parse_path(node.get('d', ''), TransformPen(pen, transform))
            return pen.bounds
        if tag == 'use':
            target = by_id.get((node.get(XLINK) or node.get('href') or '')[1:])
            box = bounds(target) if target is not None else None
        elif tag in ('image', 'rect'):
            x, y = (float(node.get(axis, 0)) for axis in ('x', 'y'))
            w, h = (float(node.get(axis, 0)) for axis in ('width', 'height'))
            box = (x, y, x + w, y + h)
        elif tag in ('defs', 'clipPath', 'mask'):
            return None
        else:
            boxes = [child_box for child in node if (child_box := bounds(child))]
            if not boxes:
                return None
            box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                   max(b[2] for b in boxes), max(b[3] for b in boxes))

        if box is None:
            return None
        x0, y0, x1, y1 = box
        a, b, c, d, e, f = transform
        points = [(a*x+c*y+e, b*x+d*y+f) for x in (x0, x1) for y in (y0, y1)]
        return (min(x for x, _ in points), min(y for _, y in points),
                max(x for x, _ in points), max(y for _, y in points))

    return bounds


def slice_svg(original, bounds, name, start, end, *, paper=False, markers=()):
    svg = deepcopy(original)
    for source, target in zip(original[-1], list(svg[-1])):
        box = bounds(source)
        if box and (box[3] <= start or box[1] >= end):
            target.getparent().remove(target)

    if paper:
        for image in svg.iter(SVG_TAG + 'image'):
            if image.get('data-lazy-href') == social_background:
                image.attrib.pop('data-lazy-href')

    defs = svg.find(SVG_TAG + 'defs')
    definition_roots = {node.get('id'): root for root in defs for node in root.iter() if node.get('id')}
    pending = list(svg_references(svg[-1].iter()))
    used = set()
    while pending:
        definition = definition_roots.get(pending.pop())
        if definition is not None and definition not in used:
            used.add(definition)
            pending.extend(svg_references(definition.iter()))
    for definition in list(defs):
        if definition not in used:
            defs.remove(definition)

    ids = {node.get('id') for node in svg.iter() if node.get('id')}
    if name != '2':
        for node in svg.iter():
            for key, value in list(node.attrib.items()):
                if key == 'id':
                    node.set(key, f'{name}-{value}')
                elif key in ('href', XLINK) and value.startswith('#') and value[1:] in ids:
                    node.set(key, f'#{name}-{value[1:]}')
                elif 'url(#' in value:
                    node.set(key, URL_REFERENCE.sub(lambda m: f'url(#{name}-{m[1]})' if m[1] in ids else m[0], value))

    height = end - start
    svg.set('viewBox', f'0 {start} 1920 {height}')
    css = ' social-paper' if paper else ''
    marker_html = ''.join(
        f'<span class="section-marker" id="{key}" data-name="{title}" style="top:{(y-start)/height*100:.7f}%">'
        f'<span class="sr-only">{title}</span></span>' for key, title, y in markers
    )
    return (f'<section class="portfolio-page portfolio-slice{css}" data-page="{name}" style="aspect-ratio:1920/{height}">'
            f'{marker_html}{etree.tostring(svg, encoding="unicode")}</section>')


def save_texture(source, output, tile):
    with Image.open(DIST / source) as image:
        image.crop(tile).resize((512, 512), Image.Resampling.LANCZOS).save(DIST / output, 'WEBP', quality=85)


def project_thumb(slug, source):
    target = f'assets/social-{slug}-cover.webp'
    with Image.open(DIST / source) as image:
        image.thumbnail((520, 360), Image.Resampling.LANCZOS)
        image.convert('RGB').save(DIST / target, 'WEBP', quality=84)
    return target


def rename_construct_captions(svg):
    """Reuse the card font paths to correct the three Ninth Art labels."""
    artwork = svg[-1]
    glyphs = {node.get('data-text'): node.get(XLINK) for node in artwork
              if (node.get(XLINK) or '').startswith('#p2-font_15_')}
    definitions = {node.get('id'): node for node in svg.iter() if node.get('id')}
    bounds = svg_bounds(svg)
    old_caption = 'DREAM HOLIDAYS'
    children = list(artwork)
    for index, first in enumerate(children):
        if first.get('data-text') != old_caption[0]:
            continue
        matrix = [float(n) for n in re.findall(NUMBER, first.get('transform', ''))]
        if len(matrix) != 6 or not 9150 < matrix[5] < 9180:
            continue
        originals = children[index:index + len(old_caption)]
        if ''.join(node.get('data-text', '') for node in originals) != old_caption:
            continue

        scale, _, _, _, x, baseline = matrix
        for letter in 'NINTH ART':
            if letter == ' ':
                x += scale * 0.25
                continue
            glyph = deepcopy(first)
            reference = glyphs[letter]
            glyph.set('data-text', letter)
            glyph.set(XLINK, reference)
            glyph.set('transform', f'matrix({scale},0,0,{-scale},{x:.4f},{baseline})')
            first.addprevious(glyph)
            left, _, right, _ = bounds(definitions[reference[1:]])
            x += scale * (left + right)
        for node in originals:
            artwork.remove(node)


def project_html(title, content, artworks):
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} — Suzan Al-Sadoun</title>
  <link rel="icon" href="icon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="style.css?v=16">
</head>
<body class="social-project-page">
  <header class="social-project-header">
    <a href="index.html#social-projects">← Back to social media</a>
    <button id="motion-toggle" class="icon-button" aria-label="Pause motion" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5v14M15 5v14"/></svg></button>
  </header>
  <main id="portfolio" class="social-paper">
    <h1 class="social-project-title">{escape(title)}</h1>
    {content}
  </main>
  {viewer}
  <script id="gallery-data" type="application/json">{json.dumps(artworks, ensure_ascii=False)}</script>
  <script src="lazy.js?v=15"></script>
  <script src="app.js?v=16"></script>
</body>
</html>
'''


def write_social_project(slug, title, ranges):
    panels = [slice_svg(social, social_bounds, f'{slug}-{i}', start, end, paper=True)
              for i, (start, end) in enumerate(ranges)]
    indices = list(dict.fromkeys(index for panel in panels
                   for index in sorted({int(value) for value in re.findall(r'data-gallery="(\d+)"', panel)})))
    local_index = {index: i for i, index in enumerate(indices)}
    pieces = re.sub(r'data-gallery="(\d+)"', lambda m: f'data-gallery="{local_index[int(m[1])]}"', ''.join(panels))
    artworks = [gallery[index] for index in indices]
    (DIST / f'{slug}.html').write_text(project_html(title, pieces, artworks))


source = INDEX.read_text()
if 'id="social-projects"' in source:
    raise SystemExit('The portfolio is already organized. Rebuild it before running this step.')
viewer = re.search(r'<dialog id="gallery-dialog".*?</dialog>', source, re.S)[0]
gallery = json.loads(GALLERY_SCRIPT.search(source)[2])
social_section = re.search(r'<section class="portfolio-page" data-page="2".*?</section>', source, re.S)[0]
variety_section = re.search(r'<section class="portfolio-page" data-page="3".*?</section>', source, re.S)[0]
social = read_svg(social_section)
variety = read_svg(variety_section)
rename_construct_captions(social)
social_bounds = svg_bounds(social)
variety_bounds = svg_bounds(variety)

social_background = next(image.get('data-lazy-href') for image in social.iter(SVG_TAG + 'image')
                         if float(image.get('data-lazy-bottom', 0)) > 13500)
variety_background = next(image.get('data-lazy-href') for image in variety.iter(SVG_TAG + 'image')
                           if float(image.get('data-lazy-top', 1000)) < 0
                           and float(image.get('data-lazy-bottom', 0)) > 7000)
save_texture(social_background, 'assets/social-paper.webp', (690, 460, 1330, 1100))
save_texture(variety_background, 'assets/variety-paper.webp', (600, 960, 1240, 1600))

social_end = float(social.get('viewBox').split()[-1])
projects = [
    ('shams-tv', 'Shams TV', ((1915, 3420),), 'Shams TV — Social media'),
    ('kurdistan-islamic-bank', 'Kurdistan Islamic Bank', ((3420, 4230),), 'Kurdistan Islamic Bank — Social media'),
    ('awamedica', 'Awamedica', ((4230, 5050),), 'Awamedica — Social media'),
    ('restaurants', 'restaurants', ((6060, 8350), (9610, 10675), (5050, 6060)), 'Jazz Bar — Social media'),
    ('flights', 'flights', ((8350, 8960),), 'Dream Holidays — Social media'),
    ('tconstruc', 'tconstruc', ((8960, 9610),), 'Ninth Art — Social media'),
    ('verity', 'verity', ((10675, social_end),), 'Ninth Art — Grid posts'),
]
cards = []
for slug, title, ranges, artwork_label in projects:
    write_social_project(slug, title, ranges)
    cover = next(art['source'] for art in gallery if art['label'] == artwork_label)
    cards.append((slug, title, project_thumb(slug, cover)))

cards_html = ''.join(
    f'<a class="social-card" href="{slug}.html"><img src="{cover}" width="520" height="360" loading="lazy" decoding="async" alt="">'
    f'<span>{escape(title)} <span aria-hidden="true">↗</span></span></a>'
    for slug, title, cover in cards
)
social_index = f'<section id="social-projects" class="social-projects social-paper" aria-label="Social media projects">{cards_html}</section>'

social_parts = (
    slice_svg(social, social_bounds, '2', 0, 1810, paper=True, markers=(('social', 'Social media', 0),)),
    social_index,
)
source = source.replace(social_section, ''.join(social_parts), 1)

# Copy the outer postage-stamp path from the first existing variety image.
first_frame = next(node for node in variety[-1] if node.get('data-gallery') and
                   gallery[int(node.get('data-gallery'))]['label'] == 'Motion design — Frames' and
                   gallery[int(node.get('data-gallery'))]['y'] < 1500)
frame_path = first_frame.getprevious().find(SVG_TAG + 'path')
x0, y0, x1, y1 = variety_bounds(frame_path)
stamp = etree.Element(SVG_TAG + 'svg', nsmap={None: SVG}, viewBox=f'{x0} {y0} {x1-x0} {y1-y0}')
stamp.append(deepcopy(frame_path))
(DIST / 'assets/variety-stamp.svg').write_bytes(etree.tostring(stamp))

variety_end = float(variety.get('viewBox').split()[-1])
video = f'''<section class="variety-video" aria-label="LED wall motion design">
<figure style="aspect-ratio:{x1-x0}/{y1-y0}"><video aria-label="Black smoke LED wall animation"
 muted loop playsinline preload="none" poster="assets/led-wall-black-smoke-poster.jpg">
 <source src="assets/led-wall-black-smoke.mp4" type="video/mp4"></video></figure>
</section>'''
variety_parts = (
    slice_svg(variety, variety_bounds, 'variety-title', 0, 1040, markers=(('variety', 'Variety', 0),)),
    video,
    slice_svg(variety, variety_bounds, 'variety-work', 1040, variety_end,
              markers=(('photography', 'Photography', 6710),)),
)
source = source.replace(variety_section, ''.join(variety_parts), 1)
main_indices = sorted({int(index) for index in re.findall(r'data-gallery="(\d+)"', source)})
main_positions = {index: i for i, index in enumerate(main_indices)}
source = re.sub(r'data-gallery="(\d+)"', lambda m: f'data-gallery="{main_positions[int(m[1])]}"', source)
source = GALLERY_SCRIPT.sub(lambda m: m[1] + json.dumps([gallery[index] for index in main_indices], ensure_ascii=False) + m[3],
                            source, count=1)
INDEX.write_text(source)
