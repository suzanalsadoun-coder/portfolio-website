const galleryData=JSON.parse(document.querySelector('#gallery-data').textContent);
const artworkNodes=[...document.querySelectorAll('.artwork')];
const shapeNodes=[...document.querySelectorAll('.floating-shape')];
const svgNS='http://www.w3.org/2000/svg';
const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
let paused=reduced.matches;
try{paused=paused||localStorage.getItem('portfolio-motion')==='paused'}catch{}
const motionButton=document.querySelector('#motion-toggle');
function updateMotion(){document.documentElement.classList.toggle('motion-paused',paused);motionButton.setAttribute('aria-pressed',String(paused));motionButton.setAttribute('aria-label',paused?'Resume motion':'Pause motion');motionButton.title=paused?'Resume motion':'Pause motion';motionButton.querySelector('svg').innerHTML=paused?'<path d="m9 5 10 7-10 7Z"/>':'<path d="M9 5v14M15 5v14"/>'}
updateMotion();motionButton.addEventListener('click',()=>{paused=!paused;updateMotion();try{localStorage.setItem('portfolio-motion',paused?'paused':'on')}catch{}});

// Use the actual PDF clipping bounds, so cropped mockups pivot about their visible centre.
for(const node of [...artworkNodes,...shapeNodes]){
  let b=JSON.parse(node.dataset.bounds);
  const clipId=node.dataset.sourceClip?.match(/url\(#([^)]*)\)/)?.[1];
  const path=clipId?document.getElementById(clipId)?.firstElementChild:null;
  if(path){try{const r=path.getBBox(),m=path.transform.baseVal.consolidate()?.matrix;const pts=[[r.x,r.y],[r.x+r.width,r.y+r.height]].map(([x,y])=>m?new DOMPoint(x,y).matrixTransform(m):{x,y});b=[Math.min(pts[0].x,pts[1].x),Math.min(pts[0].y,pts[1].y),Math.max(pts[0].x,pts[1].x),Math.max(pts[0].y,pts[1].y)]}catch{}}
  const motion=node.querySelector('.motion-layer');
  motion.style.transformBox='view-box';motion.style.transformOrigin=`${(b[0]+b[2])/2}px ${(b[1]+b[3])/2}px`;
  const spot=document.createComment('original artwork position');node.before(spot);
  node.addEventListener('pointerenter',e=>{if(e.pointerType==='touch'||paused)return;clearTimeout(node._restore);for(const other of [...artworkNodes,...shapeNodes]){if(other!==node)other.classList.remove('is-hovered')}node.classList.remove('reveal-once');if(node.classList.contains('artwork')&&node.parentElement.lastElementChild!==node)node.parentElement.append(node);node.classList.add('is-hovered')});
  node.addEventListener('pointermove',e=>{if(e.pointerType==='touch'||paused)return;const box=node.getBoundingClientRect(),x=(e.clientX-box.left)/box.width-.5,y=(e.clientY-box.top)/box.height-.5;const shape=node.classList.contains('floating-shape');node.style.setProperty('--mx',`${x*(shape?36:8)}px`);node.style.setProperty('--my',`${y*(shape?28:6)}px`);node.style.setProperty('--tilt',`${x*(shape?15:1.8)}deg`)});
  const reset=()=>{node.classList.remove('is-hovered');node.style.setProperty('--mx','0px');node.style.setProperty('--my','0px');node.style.setProperty('--tilt','0deg');clearTimeout(node._restore);node._restore=setTimeout(()=>{if(!node.classList.contains('is-hovered'))spot.after(node)},700)};
  node.addEventListener('pointerleave',reset);
  // Reparenting during mousedown/focus cancels the subsequent native click.
  node.addEventListener('blur',reset);
}

// Keep the original vector logos together, including every Arabic and English detail.
// Bounds are in the first PDF page's original coordinate system.
const brandLogoRegions=[
  {name:'Kunafa',id:'kunafa',bounds:[190,3860,505,4115],from:'translateY(15px) rotate(-4deg) scale(.94)'},
  {name:'Enmaa',id:'enmaa',bounds:[245,5540,435,5790],from:'translateY(24px) scale(.97)'},
  {name:'Misk Fashion',id:'misk',bounds:[170,6920,495,7080],from:'translateX(-22px) scale(.97)'},
  {name:'Evar Holding',id:'evar',bounds:[160,8500,515,8640],from:'translateY(10px) scale(.9)'}
];
const brandingSvg=document.querySelector('.portfolio-art');
const brandingContent=brandingSvg.querySelector(':scope > g');
const svgRect=brandingSvg.getBoundingClientRect();
const svgWidth=Number(brandingSvg.getAttribute('viewBox').split(/\s+/)[2]);
const coordinateScale=svgWidth/svgRect.width;
const logoCandidates=[...brandingContent.querySelectorAll('path,use')];
const brandLogoNodes=[];
for(const brand of brandLogoRegions){
  const [x0,y0,x1,y1]=brand.bounds;
  const parts=logoCandidates.filter(part=>{const r=part.getBoundingClientRect();const x=(r.left-svgRect.left)*coordinateScale,y=(r.top-svgRect.top)*coordinateScale;return r.width>0&&r.height>0&&x>=x0&&y>=y0&&x+r.width*coordinateScale<=x1&&y+r.height*coordinateScale<=y1});
  const parents=[...new Set(parts.map(part=>part.parentElement))];
  for(const parent of parents){
    const siblings=parts.filter(part=>part.parentElement===parent);
    const group=document.createElementNS(svgNS,'g');group.classList.add('brand-logo');group.dataset.brand=brand.id;group.setAttribute('role','img');group.setAttribute('aria-label',brand.name+' logo');
    const motion=document.createElementNS(svgNS,'g');motion.classList.add('logo-motion');motion.style.setProperty('--logo-from',brand.from);motion.style.transformBox='view-box';motion.style.transformOrigin=`${(x0+x1)/2}px ${(y0+y1)/2}px`;
    parent.insertBefore(group,siblings[0]);group.append(motion);for(const part of siblings)motion.append(part);brandLogoNodes.push(group);
  }
}
if('IntersectionObserver' in window){const logosObserver=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){entry.target.classList.add('logo-revealed');logosObserver.unobserve(entry.target)}}},{threshold:.25,rootMargin:'0px 0px -8% 0px'});for(const logo of brandLogoNodes)logosObserver.observe(logo)}else{for(const logo of brandLogoNodes)logo.classList.add('logo-revealed')}

const dialog=document.querySelector('#gallery-dialog');
const stage=document.querySelector('#viewer-image');
let current=0,opener=null,scrollPosition=0;
function showArt(index){current=(index+galleryData.length)%galleryData.length;const data=galleryData[current];const img=new Image();img.src=data.source;img.alt=data.label;stage.replaceChildren(img);document.querySelector('#art-title').textContent=data.label;document.querySelector('#art-count').textContent=`${String(current+1).padStart(2,'0')} / ${galleryData.length}`}
function openViewer(index,node){opener=node;scrollPosition=window.scrollY;showArt(index);dialog.showModal();document.body.style.overflow='hidden';document.querySelector('#close-viewer').focus()}
function closeViewer(){dialog.close()}
dialog.addEventListener('close',()=>{document.body.style.overflow='';opener?.focus({preventScroll:true});window.scrollTo({top:scrollPosition,behavior:'instant'})});
for(const node of artworkNodes){node.addEventListener('click',()=>openViewer(Number(node.dataset.gallery),node));node.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();openViewer(Number(node.dataset.gallery),node)}})}
document.querySelector('#close-viewer').addEventListener('click',closeViewer);
document.querySelector('#previous-art').addEventListener('click',()=>showArt(current-1));
document.querySelector('#next-art').addEventListener('click',()=>showArt(current+1));
dialog.addEventListener('keydown',e=>{if(e.key==='ArrowRight'){e.preventDefault();showArt(current+1)}if(e.key==='ArrowLeft'){e.preventDefault();showArt(current-1)}});
let touchX=null;stage.addEventListener('touchstart',e=>{touchX=e.changedTouches[0].screenX},{passive:true});stage.addEventListener('touchend',e=>{if(touchX===null)return;const dx=e.changedTouches[0].screenX-touchX;if(Math.abs(dx)>60)showArt(current+(dx<0?1:-1));touchX=null},{passive:true});

const markers=[...document.querySelectorAll('.section-marker')];
const links=[...document.querySelectorAll('.section-links a')];
const progress=document.querySelector('.reading-progress span');
let scrollQueued=false;
function updateScroll(){scrollQueued=false;const max=document.documentElement.scrollHeight-innerHeight;progress.style.transform=`scaleX(${max?Math.min(1,window.scrollY/max):0})`;let active=markers[0];for(const m of markers){if(m.getBoundingClientRect().top<innerHeight*.38)active=m}for(const link of links){if(link.hash==='#'+active.id)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current')}document.querySelector('#current-section').textContent=active.dataset.name}
window.addEventListener('scroll',()=>{if(!scrollQueued){scrollQueued=true;requestAnimationFrame(updateScroll)}},{passive:true});window.addEventListener('resize',updateScroll);updateScroll();
const dock=document.querySelector('.dock'),menu=document.querySelector('.mobile-menu');menu.addEventListener('click',()=>{const open=dock.classList.toggle('menu-open');menu.setAttribute('aria-expanded',String(open))});
for(const link of links)link.addEventListener('click',()=>{dock.classList.remove('menu-open');menu.setAttribute('aria-expanded','false')});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){dock.classList.remove('menu-open');menu.setAttribute('aria-expanded','false')}});
const tip=document.querySelector('.intro-tip');function dismissTip(){tip.classList.add('dismissed');setTimeout(()=>tip.remove(),600)}tip.querySelector('button').addEventListener('click',dismissTip);setTimeout(dismissTip,9000);

// Make the original contact block and the small header navigation clickable.
function addLink(svg,x,y,width,height,url,label){const a=document.createElementNS(svgNS,'a');a.setAttribute('href',url);a.setAttribute('aria-label',label);const rect=document.createElementNS(svgNS,'rect');for(const [key,val] of Object.entries({x,y,width,height,fill:'transparent'}))rect.setAttribute(key,val);a.append(rect);svg.append(a)}
const firstSvg=document.querySelector('.portfolio-art');
addLink(firstSvg,80,1980,255,55,'mailto:Suzanalsadoun@gmail.com','Email Suzan Al-Sadoun');
addLink(firstSvg,80,1925,255,55,'tel:+9647517970834','Call Suzan Al-Sadoun');
const headerLinks=[['branding',452,110],['logos',562,111],['print',673,109],['social',782,120],['variety',902,112],['photography',1014,125]];
for(const [id,x,width] of headerLinks)addLink(firstSvg,x,65,width,45,'#'+id,`Go to ${id}`);

// Reveal the actual artwork gently; the layout stays at its original PDF coordinates.
if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{for(const entry of entries){if(entry.isIntersecting){if(!paused)entry.target.classList.add('reveal-once');observer.unobserve(entry.target)}}},{threshold:.08});for(const node of artworkNodes)observer.observe(node)}
