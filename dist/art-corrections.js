// Reuse the original variety-section shape behind the print heading.
(() => {
  const reference = document.querySelector('[data-source-clip="url(#p3-clip_53)"] .motion-layer');
  if (!reference) return;
  const mask = document.getElementById('p3-mask_54');
  if (mask) for (const image of mask.querySelectorAll('image[data-lazy-href]')) {
    image.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href',image.dataset.lazyHref);
    image.removeAttribute('data-lazy-href');
  }
  for (const id of ['p1-clip_22','p1b-clip_22']) {
    const target = document.querySelector(`[data-source-clip="url(#${id})"] .motion-layer`);
    if (!target) continue;
    const group = document.createElementNS('http://www.w3.org/2000/svg','g');
    group.setAttribute('transform','matrix(0.831,0,0,1.049,292.6,3202)');
    for (const child of reference.children) group.append(child.cloneNode(true));
    for (const image of group.querySelectorAll('image')) {
      image.removeAttribute('id');
      if (image.dataset.lazyHref) {image.setAttributeNS('http://www.w3.org/1999/xlink','xlink:href',image.dataset.lazyHref);image.removeAttribute('data-lazy-href');}
    }
    target.replaceChildren(group);
  }
})();
