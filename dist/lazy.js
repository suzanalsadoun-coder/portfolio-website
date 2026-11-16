// Load visible artwork and nearby images before the viewer reaches them.
const pendingSections = [...document.querySelectorAll('.portfolio-page')];
const coverImage = document.querySelector('[data-cover-background]');
const coverSmall = window.matchMedia('(max-width: 640px)');
const coverMedium = window.matchMedia('(max-width: 1100px)');
const imageNamespace = 'http://www.w3.org/1999/xlink';

function loadCoverBackground() {
 if (!coverImage) return;
 const resource = coverSmall.matches ? coverImage.dataset.coverSmall
  : coverMedium.matches ? coverImage.dataset.coverMedium : coverImage.dataset.coverFull;
 if (coverImage.getAttributeNS(imageNamespace, 'href') !== resource) {
  coverImage.setAttributeNS(imageNamespace, 'xlink:href', resource);
 }
}

function loadPortfolioImages(margin = 1200) {
 for (const section of pendingSections) {
  const svg = section.querySelector('svg.portfolio-art');
  if (!svg) continue;
  const bounds = svg.getBoundingClientRect(), view = svg.viewBox.baseVal;
  if (bounds.bottom < -margin || bounds.top > innerHeight + margin) continue;
  const scale = bounds.width / view.width;
  for (const image of section.querySelectorAll('image[data-lazy-href]')) {
   if (image.hasAttribute('data-lazy-top')) {
    const top = Math.max(+image.dataset.lazyTop, view.y);
    const bottom = Math.min(+image.dataset.lazyBottom, view.y + view.height);
    if (bottom <= top || bounds.top + (bottom - view.y) * scale < -margin || bounds.top + (top - view.y) * scale > innerHeight + margin) continue;
   }
   image.setAttributeNS(imageNamespace, 'xlink:href', image.dataset.lazyHref);
   image.removeAttribute('data-lazy-href');
  }
 }
}
let portfolioLoadQueued = false;
function queuePortfolioImages() {
 if (portfolioLoadQueued) return;
 portfolioLoadQueued = true;
 requestAnimationFrame(() => { portfolioLoadQueued = false; loadPortfolioImages(); });
}
window.addEventListener('scroll', queuePortfolioImages, {passive:true});
window.addEventListener('resize', () => { loadCoverBackground(); queuePortfolioImages(); });
loadCoverBackground();
loadPortfolioImages(400);

const fenceFeature = document.querySelector('.fence-feature');
if (fenceFeature && 'IntersectionObserver' in window) {
 const fenceObserver = new IntersectionObserver(([entry]) => {
  fenceFeature.classList.toggle('is-near', entry.isIntersecting);
 }, {rootMargin: '600px 0px'});
 fenceObserver.observe(fenceFeature);
} else {
 fenceFeature?.classList.add('is-near');
}
