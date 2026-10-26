"""Preserve the original PDF artwork as vector layers with independent interactions."""
from pathlib import Path
import base64
import hashlib
import html
import json
import re
import shutil
import sys

import fitz
from lxml import etree as ET

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ASSETS = DIST / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
PDF = Path(sys.argv[1])
doc = fitz.open(PDF)
S = 'http://www.w3.org/2000/svg'
XL = '{http://www.w3.org/1999/xlink}href'
ns = {'s': S}
decorative = [{242, 247, 218}, {66, 68}, {116}, {157, 159, 146}]
backgrounds = [{214, 216, 229, 236, 238, 240, 245, 243}, {48, 50, 60, 62, 64, 25, 35, 45}, {81, 83}, {129, 131, 144}]
sections = [
    ('home', 'Portfolio', 0, 0),
    ('about', 'About', 0, 840),
    ('branding', 'Branding', 0, 2491),
    ('logos', 'Logofolio', 1, 0),
    ('print', 'Printables', 1, 2250),
    ('social', 'Social media', 2, 0),
    ('variety', 'Variety', 3, 0),
    ('photography', 'Photography', 3, 5050),
]

def category(n, y):
    if n == 0:
        if y < 5000: return 'Kunafa — Visual identity'
        if y < 6400: return 'Enmaa — Rebranding'
        if y < 7950: return 'Misk Fashion — Visual identity'
        return 'Evar Holding — Visual identity'
    if n == 1: return 'Print design'
    if n == 2:
        if y < 2050: return 'Shams TV — Social media'
        if y < 2650: return 'Kurdistan Islamic Bank — Social media'
        if y < 3350: return 'Awamedica — Social media'
        if y < 4100: return 'Soul Rest — Social media'
        if y < 5800: return 'Jazz Bar — Social media'
        if y < 6400: return 'Dream Holidays — Social media'
        if y < 7570: return 'Ninth Art — Social media'
        if y < 8380: return 'Bakery — Social media'
        return 'Ninth Art — Grid posts'
    if y < 3000: return 'Motion design — Frames'
    if y < 3600: return 'Photography & sketching'
    if y < 4300: return 'Blind Wave — CD cover'
    if y < 5000: return 'Song cover design'
    if y < 8000: return 'Photography — Bar & restaurant'
    return 'Photography — Bakery'

gallery = []
pages = []
gallery_nodes = []
for n, page in enumerate(doc):
    svg = ET.fromstring(page.get_svg_image(text_as_path=True).encode())
    content = svg[-1]
    refs = {e.get('id'): e for e in svg.iter() if e.get('id')}
    displayed = [e for e in content.iter() if ET.QName(e).localname == 'image' or (ET.QName(e).localname == 'use' and e.get(XL, '').startswith('#image_'))]
    infos = page.get_image_info(xrefs=True)
    assert len(displayed) == len(infos), (n, len(displayed), len(infos))
    # Externalize and deduplicate every raster, including the original soft masks.
    for e in svg.xpath('.//s:image', namespaces=ns):
        href = e.get(XL, '')
        if href.startswith('data:'):
            raw = base64.b64decode(href.split(',', 1)[1])
            ext = 'jpg' if 'image/jpeg' in href[:30] else 'png'
            name = hashlib.sha256(raw).hexdigest()[:18] + '.' + ext
            (ASSETS / name).write_bytes(raw)
            e.set(XL, 'assets/' + name)
    seen = set()
    for e, info in zip(displayed, infos):
        xref = info['xref']
        image = refs[e.get(XL)[1:]] if ET.QName(e).localname == 'use' else e
        assert (int(image.get('width')), int(image.get('height'))) == (info['width'], info['height'])
        if xref in backgrounds[n]: continue
        top = e
        while top.getparent() is not content: top = top.getparent()
        if top in seen: continue
        seen.add(top)
        is_shape = xref in decorative[n]
        outer = ET.Element(f'{{{S}}}g')
        motion = ET.SubElement(outer, f'{{{S}}}g', {'class': 'motion-layer'})
        content.replace(top, outer)
        motion.append(top)
        outer.set('class', 'floating-shape' if is_shape else 'artwork')
        outer.set('data-bounds', json.dumps([round(v, 3) for v in info['bbox']]))
        outer.set('data-source-clip', top.get('clip-path', ''))
        if not is_shape:
            label = category(n, info['bbox'][1])
            outer.set('tabindex', '0')
            outer.set('role', 'button')
            outer.set('aria-label', 'Enlarge ' + label)
            key = f'{n}-{xref}'
            outer.set('data-art-key', key)
            gallery_nodes.append(outer)
            if not any(item['key'] == key for item in gallery):
                source = 'assets/art-' + key + '.webp'
                if not (DIST / source).exists():
                    pix = fitz.Pixmap(doc, xref)
                    mask = next((im[1] for im in page.get_images() if im[0] == xref), 0)
                    if pix.colorspace and pix.colorspace.n > 3: pix = fitz.Pixmap(fitz.csRGB, pix)
                    if mask: pix = fitz.Pixmap(pix, fitz.Pixmap(doc, mask))
                    pix.pil_image().save(DIST / source, quality=94, method=6)
                gallery.append({'key': key, 'page': n, 'xref': xref, 'label': label, 'source': source, 'y': info['bbox'][1], 'x': info['bbox'][0]})
        else:
            outer.set('aria-hidden', 'true')
    # Isolate turquoise vector stars, keeping their original labels stationary.
    for e in list(content.xpath('.//s:path[@fill="#46a3a2"]', namespaces=ns)):
        if len(e.get('d', '')) < 150: continue
        parent = e.getparent()
        wrapper = ET.Element(f'{{{S}}}g', {'class': 'vector-star'})
        parent.replace(e, wrapper)
        wrapper.append(e)
    # Prefix all internal IDs so the four SVG documents can share one DOM.
    prefix = f'p{n}-'
    ids = {e.get('id') for e in svg.iter() if e.get('id')}
    for e in svg.iter():
        for k, v in list(e.attrib.items()):
            if k == 'id': e.set(k, prefix + v)
            elif v.startswith('#') and v[1:] in ids: e.set(k, '#' + prefix + v[1:])
            elif 'url(#' in v: e.set(k, re.sub(r'url\(#([^)]*)\)', lambda m: 'url(#' + prefix + m[1] + ')', v))
        if ET.QName(e).localname == 'use' and e.get('data-text') is not None: e.set('aria-hidden', 'true')
    svg.attrib.pop('width', None)
    svg.attrib.pop('height', None)
    svg.set('class', 'portfolio-art')
    svg.set('role', 'group')
    svg.set('aria-label', ['Introduction and visual identities', 'Logofolio and print design', 'Social media design', 'Variety and photography'][n])
    svg.set('preserveAspectRatio', 'xMidYMin meet')
    # Text remains vector-sharp at any screen size, without requiring missing fonts.
    markers = ''.join(f'<span class="section-marker" id="{sid}" data-name="{name}" style="top:{y / page.rect.height * 100:.7f}%"><span class="sr-only">{name}</span></span>' for sid, name, pn, y in sections if pn == n)
    pages.append(f'<section class="portfolio-page" data-page="{n}" style="aspect-ratio:{page.rect.width}/{page.rect.height}">{markers}{ET.tostring(svg, encoding="unicode")}</section>')

shutil.copy2(PDF, ASSETS / 'Suzan-Al-Sadoun-Portfolio.pdf')
template = (ROOT / 'shell.html').read_text()
template = template.replace('<!--PORTFOLIO-->', '\n'.join(pages))
gallery.sort(key=lambda item:(item['page'], item['y'], item['x']))
for index, item in enumerate(gallery):
    template = template.replace(f'data-art-key="{item["key"]}"', f'data-gallery="{index}"')
template = template.replace('/*GALLERY_DATA*/', json.dumps(gallery, ensure_ascii=False))
(DIST / 'index.html').write_text(template)
print(json.dumps({'pages':len(pages),'interactive_artworks':len(gallery),'raster_assets':len(list(ASSETS.iterdir())),'html_bytes':len(template.encode())}))
