const collections={
 social:[...['king-selection-01','king-selection-02','king-selection-03','chicken-fries-01','chicken-fries-02','chicken-fries-03','chicken-fries-04','chicken-fries-05','king-box-01','king-box-02','world-cup-01','world-cup-02','world-cup-03','world-cup-04','world-cup-05','world-cup-06'],...Array.from({length:16},(_,i)=>`calendar-${String(i+1).padStart(2,'0')}`)],
 screens:['digital-menu-01','digital-menu-02','digital-menu-03'],
 print:['sidewalk-01','drive-through-04','drive-through-05','baghdad-billboard-06','printed-menu-07','printed-menu-08','packaging-selection-new']
};
for(const section of document.querySelectorAll('[data-gallery]')){
 const items=collections[section.dataset.gallery],img=section.querySelector('img'),counter=section.querySelector('.counter');let index=0,timer;
 function show(i){index=(i+items.length)%items.length;img.src=`assets/bk/${items[index]}.webp`;counter.textContent=`${String(index+1).padStart(2,'0')} / ${String(items.length).padStart(2,'0')}`;}
 function schedule(){clearInterval(timer);if(!window.matchMedia('(prefers-reduced-motion: reduce)').matches)timer=setInterval(()=>{if(!document.hidden)show(index+1)},2000)}
 section.querySelector('.prev').addEventListener('click',()=>{show(index-1);schedule()});section.querySelector('.next').addEventListener('click',()=>{show(index+1);schedule()});section.addEventListener('mouseenter',()=>clearInterval(timer));section.addEventListener('mouseleave',schedule);section.addEventListener('focusin',()=>clearInterval(timer));section.addEventListener('focusout',schedule);show(0);schedule();
}
const motionVideos = [...document.querySelectorAll('.videos video')];
for (const video of motionVideos) video.playbackRate = 1.5;
if ('IntersectionObserver' in window) {
 const videoObserver = new IntersectionObserver(entries => {
  for (const entry of entries) {
   if (entry.isIntersecting && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) entry.target.play().catch(() => {});
   else entry.target.pause();
  }
 }, {threshold: 0.25});
 motionVideos.forEach(video => videoObserver.observe(video));
}

