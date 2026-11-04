"""Load portfolio SVG images when their section approaches the viewport."""
from pathlib import Path
import re
root=Path(__file__).resolve().parent
path=root/'dist/index.html'
s=path.read_text()
def defer(match):
    block=match.group(0)
    def transform(tag):
        return re.sub(r'\s(?:xlink:href|href)="(assets/[^"#]+)"',r' data-lazy-href="\1"',tag.group(0))
    return re.sub(r'<image\b[^>]*>',transform,block)
s=re.sub(r'<section class="portfolio-page".*?</section>',defer,s,flags=re.S)
s=s.replace('<img class="fence-background"','<img loading="lazy" class="fence-background"').replace('<img src="assets/fence-strip.webp"','<img loading="lazy" src="assets/fence-strip.webp"')
s=s.replace('<script src="app.js?v=2"></script>','<script src="lazy.js?v=1"></script><script src="app.js?v=3"></script>')
path.write_text(s)
