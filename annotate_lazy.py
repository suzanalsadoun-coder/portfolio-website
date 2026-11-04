"""Map PDF image placements to scroll ranges for incremental SVG loading."""
from pathlib import Path
import base64,hashlib,io,re,sys
import fitz
from lxml import etree as ET
from PIL import Image
root=Path(__file__).resolve().parent; path=root/'dist/index.html';text=path.read_text();doc=fitz.open(sys.argv[1]);XL='{http://www.w3.org/1999/xlink}href'
ranges=[]
for page in doc:
 svg=ET.fromstring(page.get_svg_image(text_as_path=True).encode(),ET.XMLParser(huge_tree=True));content=svg[-1];refs={e.get('id'):e for e in svg.iter() if e.get('id')};displayed=[e for e in content.iter() if ET.QName(e).localname=='image' or (ET.QName(e).localname=='use' and e.get(XL,'').startswith('#image_'))];infos=page.get_image_info(xrefs=True);assert len(displayed)==len(infos);r={}
 for e,info in zip(displayed,infos):
  im=refs[e.get(XL)[1:]] if ET.QName(e).localname=='use' else e
  href=im.get(XL,'')
  if not href.startswith('data:'):continue
  raw=base64.b64decode(href.split(',',1)[1]); digest=hashlib.sha256(raw).hexdigest()[:18]
  with Image.open(io.BytesIO(raw)) as pic:ext='.webp' if pic.mode in ('RGB','CMYK') else ('.jpg' if 'image/jpeg' in href[:30] else '.png')
  name=digest+ext;top,bottom=info['bbox'][1],info['bbox'][3]
  if name in r:r[name]=(min(r[name][0],top),max(r[name][1],bottom))
  else:r[name]=(top,bottom)
 ranges.append(r)
def add(m):
 block=m.group();p=re.search(r'data-page="(\d+)(?:b)?"',block)
 if not p:return block
 values=ranges[int(p.group(1))]
 def attach(t):
  tag=t.group();a=re.search(r'data-lazy-href="assets/([^"/]+)"',tag)
  if a and a.group(1) in values:
   lo,hi=values[a.group(1)];return tag[:-2]+f' data-lazy-top="{lo:.1f}" data-lazy-bottom="{hi:.1f}"/>'
  return tag
 return re.sub(r'<image\b[^>]*/>',attach,block)
text=re.sub(r'<section class="portfolio-page".*?</section>',add,text,flags=re.S);path.write_text(text)
print('scroll-mapped images',text.count('data-lazy-top='))
