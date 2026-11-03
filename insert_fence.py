from pathlib import Path
import re
path=Path(__file__).resolve().parent / 'dist/index.html';s=path.read_text(); start=s.index('<section class="portfolio-page" data-page="1"');end=s.index('</section>',start)+len('</section>');old=s[start:end]
svg=old[old.index('<svg'):old.index('</svg>')+6]
first=svg.replace('viewBox="0 0 1920 10564"','viewBox="0 0 1920 4410" style="overflow:hidden"',1)
second=svg.replace('p1-','p1b-').replace('viewBox="0 0 1920 10564"','viewBox="0 4410 1920 6154" style="overflow:hidden"',1)
def disable_outside(match,lo,hi):
 tag=match.group(0);m=re.search(r'data-bounds="\[([^]]+)\]"',tag)
 if not m:return tag
 nums=[float(x.strip()) for x in m.group(1).split(',')]
 return tag.replace('class="artwork"','class="artwork-offscreen"').replace('tabindex="0"','tabindex="-1"') if nums[3]<=lo or nums[1]>=hi else tag
pattern=r'<g class="artwork"[^>]*>'
first=re.sub(pattern,lambda m:disable_outside(m,0,4410),first);second=re.sub(pattern,lambda m:disable_outside(m,4410,10564),second)
markers='''<span class="section-marker" id="logos" data-name="Logofolio" style="top:0%"><span class="sr-only">Logofolio</span></span><span class="section-marker" id="print" data-name="Printables" style="top:71.8367%"><span class="sr-only">Printables</span></span>'''
fence='''<section class="fence-feature" aria-label="4 Bridges fence design"><div class="fence-scene"><img class="fence-background" src="assets/fence-full.webp" alt="4 Bridges printed fence at night"><div class="fence-window" aria-hidden="true"><div class="fence-track"><img src="assets/fence-strip.webp" alt=""><img src="assets/fence-strip.webp" alt=""></div></div></div></section>'''
new='<section class="portfolio-page print-intro" data-page="1" style="aspect-ratio:1920/4410">'+markers+first+'</section>'+fence+'<section class="portfolio-page print-rest" data-page="1b" style="aspect-ratio:1920/6154">'+second+'</section>'
path.write_text(s[:start]+new+s[end:])
