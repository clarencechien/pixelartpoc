'use strict';
const places = [
  { id:'bridge', name:'中正橋', en:'Zhongzheng Bridge', kind:'河岸地標', lat:25.02012, lon:121.51555,
    pin:[222,127,44], note:'中正橋跨過新店溪，連起永和與台北。沿著白色橋拱旋轉視角，一側是河濱球場，另一側是緊貼堤岸的住宅街廓。' },
  { id:'dingxi', name:'頂溪站', en:'Dingxi Station', kind:'捷運街角', lat:25.014196, lon:121.515482,
    pin:[192,160,15], note:'頂溪站二號出口開在永和路上。捷運藏在地底，地面上的出口、騎樓和密集的巷道，連起通勤者的日常路線。' },
  { id:'lehua', name:'樂華夜市', en:'Lehua Night Market', kind:'夜市街區', lat:25.00872, lon:121.51372,
    pin:[237,212,8], note:'永平路是樂華夜市的主街。從上方看，成排的彩色棚頂穿過彎曲街廓，勾出永和人熟悉的逛夜市路線。' }
];
const get = id => document.getElementById(id);
const viewport = get('viewport'), canvas = get('map'), ctx = canvas.getContext('2d');
const cache = new Map();
const homeAngle = -.59;
let active = 0, model, angle = homeAngle, zoom = 1, flat = false, labels = true;
let panX = 0, panY = 0, drag = new Map(), frame = 0;
const ordinal = n => String(n+1).padStart(2,'0');
get('labels').innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.3"/></svg>';
get('reset').innerHTML='<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="6.7"/><path d="M12 2v5m0 10v5M2 12h5m10 0h5"/><circle cx="12" cy="12" r="1.1"/></svg>';
places.forEach((p,i) => {
  const button=document.createElement('button');
  button.className='place';
  button.innerHTML='<span class="thumb"><img src="assets/'+p.id+'-icon.png" alt=""></span><span class="place-copy"><strong>'+p.name+'</strong><small>'+p.en+'</small></span><span class="idx">'+ordinal(i)+'</span>';
  button.onclick=()=>select(i);
  get('places').append(button);
});
async function load(id) {
  const response=await fetch('assets/'+id+'.json');
  if(!response.ok) throw Error('missing scene');
  const data=await response.json();
  data.images=await Promise.all(data.sheets.map(name=>new Promise((resolve,reject)=>{
    const img=new Image(); img.onload=()=>resolve(img); img.onerror=reject; img.src='assets/'+name;
  })));
  return data;
}
function resetCamera() {
  angle=homeAngle; zoom=1; panX=panY=0; invalidate();
}
async function select(index) {
  const place=places[index]; active=index; model=null;
  Array.from(get('places').children).forEach((el,i)=>el.setAttribute('aria-current',String(index===i)));
  get('description').textContent=place.note; get('pin-name').textContent=place.name;
  get('pin-no').textContent=ordinal(index); get('pin').hidden=true;
  get('scene-kind').textContent=place.kind; get('scene-en').textContent=place.en;
  get('google').href='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(place.lat+','+place.lon);
  get('earth').href='https://earth.google.com/web/@'+place.lat+','+place.lon+',10a,'+(index===0?780:320)+'d,35y,32h,57t,0r';
  get('coords').textContent=place.lat.toFixed(5)+'° N  '+place.lon.toFixed(5)+'° E';
  get('loading').textContent='載入像素圖層中…'; get('loading').hidden=false;
  resetCamera();
  try {
    if(!cache.has(place.id)) cache.set(place.id,load(place.id));
    const loaded=await cache.get(place.id);
    if(index!==active)return;
    model=loaded; get('loading').hidden=true; invalidate();
  } catch {
    cache.delete(place.id);
    if(index===active) get('loading').textContent='無法載入地圖，請點選地標重試。';
  }
}
function polygon(points,color) {
  ctx.fillStyle=color;ctx.beginPath();
  points.forEach(([x,y],i)=>i?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath();ctx.fill();
}
function draw() {
  frame=0;
  const W=viewport.clientWidth,H=viewport.clientHeight;
  if(!W||!H)return;
  // One logical screen pixel per art pixel preserves hard edges even on high-DPI screens.
  if(canvas.width!==W||canvas.height!==H){canvas.width=W;canvas.height=H;}
  ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,W,H);ctx.imageSmoothingEnabled=false;
  if(!model)return;
  const n=model.size,c=Math.cos(angle),s=Math.sin(angle);
  const pitch=flat?1:.60, lift=flat?0:.90;
  const homeExtent=1.40, padding= W<510 ? .94 : .91;
  const k=Math.min(W*padding/(n*homeExtent),H*.78/(n*homeExtent*(flat?1:.60)+n*(flat?0:.08)))*zoom;
  const ox=W*.50+panX, oy=H*(flat?.50:.52)+panY;
  function point(x,y,z=0){x-=n/2;y-=n/2;return [ox+k*(x*c-y*s),oy+k*(pitch*(x*s+y*c)-z*lift)];}
  const rim=[[0,0],[n,0],[n,n],[0,n]].map(([x,y])=>point(x,y));
  if(!flat){
    const depth=k*(n*.026);
    for(let j=6;j>0;j--) {
      polygon(rim.map(([x,y])=>[ox+(x-ox)*(1+j*.003)+5+j*.6,oy+(y-oy)*(1+j*.003)+depth+3+j*.65]),'rgba(53,72,46,.038)');
    }
    rim.forEach(([x,y],i)=>{
      const [u,v]=rim[(i+1)%4];
      if(u>x)return;
      const band=(a,b,color)=>polygon([[x,y+a],[u,v+a],[u,v+b],[x,y+b]],color);
      band(0,depth,'#766b55');band(0,depth*.29,'#a09a75');band(depth*.29,depth*.48,'#b1a07b');band(depth*.82,depth,'#635f4e');
      // Small broken strata follow the cut face at the same scale as the terrain.
      for(let j=3;j<52;j+=3){
        const f=j/53,g=Math.min(1,f+.021);
        const a=[x+(u-x)*f,y+(v-y)*f+depth*.62], b=[x+(u-x)*g,y+(v-y)*g+depth*.62];
        polygon([a,b,[b[0],b[1]+Math.max(1,k)],[a[0],a[1]+Math.max(1,k)]],j%2?'#978263':'#887c60');
      }
    });
  }
  // Rotate and squash every horizontal sprite about the same origin, then lift by z.
  const [tx,ty]=point(0,0);
  model.frames.forEach((f,z)=>{
    if(!f)return;
    const [sheet,sx,sy,w,h,x,y]=f;
    const render=(height)=>{
      ctx.setTransform(k*c,k*pitch*s,-k*s,k*pitch*c,tx,ty-height*k*lift);
      ctx.drawImage(model.images[sheet],sx,sy,w,h,x,y,w,h);
    };
    if(!flat && z>0)render(z-.48);
    render(z);
  });
  ctx.setTransform(1,0,0,1,0,0);
  const [px,py]=point(...places[active].pin);const pin=get('pin');
  pin.style.left=px+'px';pin.style.top=(py-19)+'px';pin.hidden=!labels||px<24||px>W-24||py<48||py>H-10;
  get('needle').style.transform='rotate('+Math.atan2(s,c*pitch)+'rad)';
  const meters=([10,20,50,100,200].find(v=>v*k/model.unit>33)??200);
  get('scale').textContent=meters+' m';get('scale').style.setProperty('--bar',Math.round(meters*k/model.unit)+'px');
  get('out').disabled=zoom<=.651;get('in').disabled=zoom>=3.19;

}
function invalidate(){if(!frame)frame=requestAnimationFrame(draw);}
function scaleBy(factor){zoom=Math.min(3.2,Math.max(.65,zoom*factor));invalidate();}
function rotate(delta){angle+=delta;invalidate();}
function move(x,y){panX=Math.min(viewport.clientWidth*.55,Math.max(-viewport.clientWidth*.55,panX+x));panY=Math.min(viewport.clientHeight*.55,Math.max(-viewport.clientHeight*.55,panY+y));invalidate();}
function mode(value){flat=value;get('iso').setAttribute('aria-pressed',String(!flat));get('plan').setAttribute('aria-pressed',String(flat));invalidate();}
get('iso').onclick=()=>mode(false);get('plan').onclick=()=>mode(true);
get('labels').onclick=()=>{labels=!labels;get('labels').setAttribute('aria-pressed',String(labels));invalidate();};
get('reset').onclick=()=>{mode(false);resetCamera();};
get('left').onclick=()=>rotate(-Math.PI/8);get('right').onclick=()=>rotate(Math.PI/8);
get('out').onclick=()=>scaleBy(1/1.23);get('in').onclick=()=>scaleBy(1.23);
get('help').onclick=()=>{const panel=get('help-panel');panel.hidden=!panel.hidden;get('help').setAttribute('aria-expanded',String(!panel.hidden));};
viewport.addEventListener('wheel',e=>{e.preventDefault();scaleBy(Math.exp(-Math.sign(e.deltaY)*.11));},{passive:false});
viewport.addEventListener('pointerdown',e=>{
  if(e.target.closest('button,#help-panel')||e.button!==0)return;
  viewport.setPointerCapture(e.pointerId);viewport.focus({preventScroll:true});
  drag.set(e.pointerId,[e.clientX,e.clientY]);viewport.classList.add('dragging');
});
viewport.addEventListener('pointermove',e=>{
  const old=drag.get(e.pointerId);if(!old)return;
  const next=[e.clientX,e.clientY];
  if(drag.size===2){
    const other=[...drag].find(([id])=>id!==e.pointerId)[1];
    const distance=p=>Math.hypot(p[0]-other[0],p[1]-other[1]);
    if(distance(old)>4)scaleBy(distance(next)/distance(old));
    move((next[0]-old[0])/2,(next[1]-old[1])/2);
  }else if(e.shiftKey || flat)move(next[0]-old[0],next[1]-old[1]);
  else rotate((next[0]-old[0])*.009);
  drag.set(e.pointerId,next);
});
function release(e){drag.delete(e.pointerId);if(!drag.size)viewport.classList.remove('dragging');}
['lostpointercapture','pointerup','pointercancel'].forEach(type=>viewport.addEventListener(type,release));
viewport.addEventListener('keydown',e=>{
  if(e.target!==viewport)return;
  const key=e.key;if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Home','Escape'].includes(key))return;
  e.preventDefault();
  if(key==='Home')get('reset').click();
  else if(key==='Escape'){get('help-panel').hidden=true;get('help').setAttribute('aria-expanded','false');}
  else if(key==='+'||key==='=')scaleBy(1.2);
  else if(key==='-')scaleBy(1/1.2);
  else if(key==='ArrowUp'||key==='ArrowDown')move(0,key==='ArrowUp'?-24:24);
  else if(e.shiftKey)move(key==='ArrowLeft'?-24:24,0);
  else rotate(key==='ArrowLeft'?-.15:.15);
});
new ResizeObserver(invalidate).observe(viewport);
select(0);
