// Reuse the original variety-section shape behind the print heading.
function applyPrintShape() {
  const reference = document.querySelector('[data-decoration="variety"] .motion-layer');
  if (!reference) return;
  for (const node of reference.querySelectorAll('[mask]')) {
    const id = node.getAttribute('mask').match(/^url\(#([^)]*)\)$/)?.[1];
    const mask = document.getElementById(id);
    if (!mask) continue;
    for (const image of mask.querySelectorAll('image[data-lazy-href]')) {
      image.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href',image.dataset.lazyHref);
      image.removeAttribute('data-lazy-href');
    }
  }
  for (const target of document.querySelectorAll('[data-decoration="print"] .motion-layer')) {
    const group = document.createElementNS('http://www.w3.org/2000/svg','g');
    group.setAttribute('transform','matrix(0.831,0,0,1.049,292.6,3202)');
    for (const child of reference.children) group.append(child.cloneNode(true));
    for (const image of group.querySelectorAll('image')) {
      image.removeAttribute('id');
      if (image.dataset.lazyHref) {image.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href',image.dataset.lazyHref);image.removeAttribute('data-lazy-href');}
    }
    target.replaceChildren(group);
  }
}

const printIntro = document.querySelector('.print-intro');
if (printIntro && 'IntersectionObserver' in window) {
  const printObserver = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    printObserver.disconnect();
    applyPrintShape();
  }, {rootMargin: '1000px 0px'});
  printObserver.observe(printIntro);
} else {
  applyPrintShape();
}
