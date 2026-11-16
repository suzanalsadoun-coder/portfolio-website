"""Preserve the original PDF artwork as vector layers with independent interactions."""
from pathlib import Path
import base64
import hashlib
import html
import io
import json
import re
import runpy
import shutil
import sys

import fitz
from PIL import Image
from lxml import etree as ET

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ASSETS = DIST / 'assets'
ASSETS.mkdir(parents=True, exist_ok=True)
PDF = Path(sys.argv[1])
with PDF.open('rb') as pdf_file:
    pdf_digest = hashlib.file_digest(pdf_file, 'sha256').hexdigest()[:12]
doc = fitz.open(PDF)
S = 'http://www.w3.org/2000/svg'
XL = '{http://www.w3.org/1999/xlink}href'
ns = {'s': S}
# Image references for the source PDF, grouped by page. The named decorations
# carry the motion even when MuPDF assigns their clipping paths new IDs.
decorations = [
    {243: 'portfolio', 234: 'branding', 249: 'about'},
    {70: 'print', 72: 'logos'},
    {101: 'social'},
    {161: 'thanks', 163: 'photography', 150: 'variety'},
]
backgrounds = [
    {207, 227, 229, 232, 247, 251, 253, 255, 257},
    {29, 39, 49, 52, 54, 64, 66, 68, 207},
    {85, 87},
    {133, 135, 148},
]
sections = [
    ('home', 'Portfolio', 0, 0),
    ('about', 'About', 0, 2125),
    ('branding', 'Branding', 0, 3203),
    ('logos', 'Logofolio', 1, 0),
    ('print', 'Printables', 1, 3168),
    ('social', 'Social media', 2, 0),
    ('variety', 'Variety', 3, 0),
    ('photography', 'Photography', 3, 6710),
]

def category(n, y):
    if n == 0:
        if y < 6500: return 'Kunafa — Visual identity'
        if y < 8400: return 'Enmaa — Rebranding'
        if y < 10600: return 'Misk Fashion — Visual identity'
        return 'Evar Holding — Visual identity'
    if n == 1: return 'Print design'
    if n == 2:
        if y < 2000: return 'Burger King — Social media'
        if y < 3500: return 'Shams TV — Social media'
        if y < 4300: return 'Kurdistan Islamic Bank — Social media'
        if y < 5200: return 'Awamedica — Social media'
        if y < 6100: return 'Soul Rest — Social media'
        if y < 8400: return 'Jazz Bar — Social media'
        if y < 9100: return 'Dream Holidays — Social media'
        if y < 9600: return 'Ninth Art — Social media'
        if y < 10800: return 'Bakery — Social media'
        return 'Ninth Art — Grid posts'
    if y < 3900: return 'Motion design — Frames'
    if y < 4800: return 'Photography & sketching'
    if y < 5600: return 'Blind Wave — CD cover'
    if y < 6600: return 'Song cover design'
    if y < 10335: return 'Photography — Bar & restaurant'
    return 'Photography — Bakery'

gallery = []
pages = []
gallery_nodes = []
for n, page in enumerate(doc):
    # Image-heavy portfolio PDFs can contain very large embedded data URLs.
    svg = ET.fromstring(page.get_svg_image(text_as_path=True).encode(), ET.XMLParser(huge_tree=True))
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
            digest = hashlib.sha256(raw).hexdigest()[:18]
            with Image.open(io.BytesIO(raw)) as extracted:
                if extracted.mode in ('RGB', 'CMYK'):
                    image = extracted.point(lambda value: 255-value).convert('RGB') if extracted.mode == 'CMYK' else extracted.copy()
                    image.thumbnail((2400, 14000))
                    name = digest + '.webp'
                    image.save(ASSETS / name, 'WEBP', quality=89, method=4)
                else:
                    name = digest + ('.jpg' if 'image/jpeg' in href[:30] else '.png')
                    (ASSETS / name).write_bytes(raw)
            e.set(XL, 'assets/' + name)
    seen = set()
    for e, info in zip(displayed, infos):
        xref = info['xref']
        image = refs[e.get(XL)[1:]] if ET.QName(e).localname == 'use' else e
        assert (int(image.get('width')), int(image.get('height'))) == (info['width'], info['height'])
        if n == 0 and xref == 229:
            image.set('data-cover-background', '')
        if n == 1 and xref == 66:
            # The typing animation uses pixel-aligned copies of this same image.
            image.set(XL, 'assets/typewriter-highres.png')
        if xref in backgrounds[n]: continue
        top = e
        while top.getparent() is not content: top = top.getparent()
        if top in seen: continue
        seen.add(top)
        if n == 2 and xref == 120:
            cover = ET.Element(f'{{{S}}}g', {'id': 'bk-teaser'})
            defs = ET.SubElement(cover, f'{{{S}}}defs')
            clip = ET.SubElement(defs, f'{{{S}}}clipPath', {'id': 'bk-teaser-clip'})
            ET.SubElement(clip, f'{{{S}}}rect', {'x':'266','y':'1240','width':'1368','height':'490','rx':'52'})
            ET.SubElement(cover, f'{{{S}}}image', {'id':'bk-teaser-image','x':'266','y':'1240','width':'1368','height':'490','preserveAspectRatio':'xMidYMid slice','clip-path':'url(#bk-teaser-clip)','href':'assets/bk/king-selection-01.webp'})
            content.replace(top, cover)
            continue
        decoration = decorations[n].get(xref)
        outer = ET.Element(f'{{{S}}}g')
        motion = ET.SubElement(outer, f'{{{S}}}g', {'class': 'motion-layer'})
        content.replace(top, outer)
        motion.append(top)
        outer.set('class', 'floating-shape category-shape' if decoration else 'artwork')
        outer.set('data-bounds', json.dumps([round(v, 3) for v in info['bbox']]))
        outer.set('data-source-clip', top.get('clip-path', ''))
        if not decoration:
            label = 'Vinery — Social media' if n == 2 and xref == 98 else category(n, info['bbox'][1])
            outer.set('tabindex', '0')
            outer.set('role', 'button')
            outer.set('aria-label', 'Enlarge ' + label)
            key = f'{n}-{xref}'
            outer.set('data-art-key', key)
            gallery_nodes.append(outer)
            if not any(item['key'] == key for item in gallery):
                # PDF object numbers can be reused for different images after
                # an edit, so include the document hash in cached filenames.
                source = 'assets/art-' + pdf_digest + '-' + key + '.webp'
                if not (DIST / source).exists() or (DIST / source).stat().st_size == 0:
                    pix = fitz.Pixmap(doc, xref)
                    mask = next((im[1] for im in page.get_images() if im[0] == xref), 0)
                    if pix.colorspace and pix.colorspace.n > 3: pix = fitz.Pixmap(fitz.csRGB, pix)
                    if mask: pix = fitz.Pixmap(pix, fitz.Pixmap(doc, mask))
                    image = pix.pil_image()
                    # Large print originals are much bigger than the viewer;
                    # keep enough resolution for screens without huge files.
                    image.thumbnail((2560, 2560))
                    image.save(DIST / source, quality=90, method=4)
                gallery.append({'key': key, 'page': n, 'xref': xref, 'label': label, 'source': source, 'y': info['bbox'][1], 'x': info['bbox'][0]})
        else:
            outer.set('data-decoration', decoration)
            outer.set('aria-hidden', 'true')
    # Isolate turquoise vector stars, keeping their original labels stationary.
    for e in list(content.xpath('.//s:path[@fill="#46a3a2" or @fill="#45a2a1"]', namespaces=ns)):
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

# Prepare a lightweight screen-resolution PDF for the website download.
download_pdf = fitz.open()
for page in doc:
    scale = 1600 / page.rect.width
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    image = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=83, optimize=True)
    download_page = download_pdf.new_page(width=page.rect.width, height=page.rect.height)
    download_page.insert_image(download_page.rect, stream=buffer.getvalue())
download_path = ASSETS / 'Suzan-Al-Sadoun-Portfolio.pdf'
if download_path.exists(): download_path.unlink()
download_pdf.save(download_path, deflate=True)
template = (ROOT / 'shell.html').read_text()
template = template.replace('<!--PORTFOLIO-->', '\n'.join(pages))
gallery.sort(key=lambda item:(item['page'], item['y'], item['x']))
for index, item in enumerate(gallery):
    template = template.replace(f'data-art-key="{item["key"]}"', f'data-gallery="{index}"')
template = template.replace('/*GALLERY_DATA*/', json.dumps(gallery, ensure_ascii=False))
template = template.replace('p2-bk-teaser', 'bk-teaser')
(DIST / 'index.html').write_text(template)
runpy.run_path(str(ROOT / 'insert_fence.py'))
runpy.run_path(str(ROOT / 'optimize_site.py'))
runpy.run_path(str(ROOT / 'annotate_lazy.py'))
runpy.run_path(str(ROOT / 'organize_portfolio.py'))
print(json.dumps({'pages':len(pages),'interactive_artworks':len(gallery),'raster_assets':len(list(ASSETS.iterdir())),'html_bytes':len(template.encode())}))
