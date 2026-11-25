import {loadDistrict} from './district-render.js';

const places=[
  {id:'bridge',name:'中正橋',en:'Zhongzheng Bridge',kind:'河岸地標',lon:121.51555,lat:25.02012,z:49,span:540,note:'白色橋拱跨過新店溪。往南平移越過河濱，再沿永和路走，就是頂溪站。'},
  {id:'dingxi',name:'頂溪站',en:'Dingxi Station',kind:'捷運街角',lon:121.515482,lat:25.014196,z:7,span:350,note:'二號出口位在永和路二段。從這裡往北接中正橋，往南則能沿著商店街走到樂華夜市。'},
  {id:'lehua',name:'樂華夜市',en:'Lehua Night Market',kind:'夜市街區',lon:121.51372,lat:25.00872,z:5,span:330,note:'永平路上的彩色棚架沿街彎進街區。放大高精度地圖，可以看到攤棚條紋、水塔和周邊公寓的窗格。'}
];
const $=id=>document.getElementById(id);
const viewport=$('viewport'),cam={x:0,y:0,angle:-.45,zoom:1,pitch:.68};
const homeNote=$('description').textContent;
const query=new URLSearchParams(location.search);
let fine=query.get('quality')!=='low',selected=-1,showRoute=true,scene,tween,frame,homeScale=.15,ready=false;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const pins=[],cards=[],touches=new Map();
const svgNS='http://www.w3.org/2000/svg';
const lines=document.createElementNS(svgNS,'svg');
lines.setAttribute('aria-hidden','true');lines.classList.add('journey');viewport.insertBefore(lines,$('pins'));
const paths=[0,1].map(()=>{const p=document.createElementNS(svgNS,'path');lines.append(p);return p;});
places.forEach((p,i)=>{
  const num=String(i+1).padStart(2,'0');
  const btn=document.createElement('button');btn.className='place';
  btn.innerHTML='<span class="thumb"><img alt="" src="assets/'+p.id+'-icon.png"></span><span class="place-copy"><strong>'+p.name+'</strong><small>'+p.en+'</small></span><span class="idx">'+num+'</span>';
  btn.onclick=()=>focusPlace(i);$('places').append(btn);cards.push(btn);
  const pin=document.createElement('button');pin.hidden=true;pin.className='map-pin';pin.setAttribute('aria-label','前往'+p.name);
  pin.innerHTML='<span>'+num+'</span>'+p.name;pin.onclick=()=>focusPlace(i);$('pins').append(pin);pins.push(pin);
});
function world(lon,lat){
  const d=scene.data;return [(lon-d.origin[0])*d.metersPerDegree[0],(lat-d.origin[1])*d.metersPerDegree[1]];
}
function project(x,y,z=0){
  const c=Math.cos(cam.angle),s=Math.sin(cam.angle);x-=cam.x;y-=cam.y;
  return [viewport.clientWidth/2+cam.zoom*(x*c-y*s),viewport.clientHeight/2+cam.zoom*((x*s+y*c)*cam.pitch-z*Math.sqrt(1-cam.pitch**2))];
}
function inverse(dx,dy){
  dx/=cam.zoom;dy/=(cam.zoom*cam.pitch);const c=Math.cos(cam.angle),s=Math.sin(cam.angle);return [dx*c+dy*s,-dx*s+dy*c];
}
function draw(time){
  frame=0;if(!ready)return;
  if(tween){
    const t=Math.min(1,(time-tween.start)/tween.duration),e=t*t*(3-2*t);
    for(const key of ['x','y','angle','pitch'])cam[key]=tween.from[key]+e*(tween.to[key]-tween.from[key]);
    cam.zoom=Math.exp(Math.log(tween.from.zoom)*(1-e)+Math.log(tween.to.zoom)*e);
    if(t>=1)tween=null;
  }
  const w=viewport.clientWidth,h=viewport.clientHeight;
  scene.draw(cam,w,h,fine);
  const placed=[];
  places.forEach((place,i)=>{
    const [x,y]=project(...world(place.lon,place.lat),scene.flat?0:place.z);
    let lift=12;for(const prior of placed)if(Math.abs(prior[0]-x)<85 && Math.abs(prior[1]-(y-lift))<27)lift+=28;
    placed.push([x,y-lift]);const pin=pins[i];
    pin.hidden=x<12||x>w-12||y<23||y>h+3;pin.style.left=x+'px';pin.style.top=(y-lift)+'px';pin.style.setProperty('--stem',(lift-3)+'px');
  });
  lines.style.display=showRoute?'':'none';
  if(showRoute)scene.data.route.forEach((segment,i)=>{
    paths[i].setAttribute('d',segment.map(([x,y],j)=>{
      const onBridge=i===0 && y<world(121.5156,25.0176)[1];
      const [a,b]=project(x,y,scene.flat?0:(onBridge?10:.4));
      return (j?'L':'M')+a.toFixed(1)+' '+b.toFixed(1);
    }).join(' '));
  });
  $('needle').style.transform='rotate('+Math.atan2(Math.sin(cam.angle),Math.cos(cam.angle)*cam.pitch)+'rad)';
  const meters=[5,10,20,50,100,200,500,1000].find(m=>m*cam.zoom>=28)??1000;
  $('scale').textContent=meters+' m';$('scale').style.setProperty('--bar',Math.round(meters*cam.zoom)+'px');
  const d=scene.data;$('coords').textContent=(d.origin[1]+cam.y/d.metersPerDegree[1]).toFixed(5)+'° N  '+(d.origin[0]+cam.x/d.metersPerDegree[0]).toFixed(5)+'° E';
  $('topdown').setAttribute('aria-pressed',String(cam.pitch===1));
  $('out').disabled=cam.zoom<=homeScale*.81;$('in').disabled=cam.zoom>=5.99;
  if(tween)invalidate();
}
function invalidate(){if(!frame)frame=requestAnimationFrame(draw);}
function go(to,animate){
  tween=null;
  if(animate&&!reduced)tween={start:performance.now(),duration:560,from:{...cam},to};
  else Object.assign(cam,to);
  invalidate();
}
function homeCamera(){
  const pitch=.68,angle=-.45,c=Math.cos(angle),s=Math.sin(angle);
  const vertices=scene.data.outline.flat();
  const px=vertices.map(([x,y])=>x*c-y*s),py=vertices.map(([x,y])=>(x*s+y*c)*pitch);
  const xmin=Math.min(...px),xmax=Math.max(...px),ymin=Math.min(...py)-28,ymax=Math.max(...py)+18;
  const midx=(xmin+xmax)/2,midy=(ymin+ymax)/(2*pitch);
  homeScale=Math.min(viewport.clientWidth*.89/(xmax-xmin),viewport.clientHeight*.75/(ymax-ymin));
  return {x:midx*c+midy*s,y:-midx*s+midy*c,zoom:homeScale,angle,pitch};
}
function writeUrl(){
  const url=new URL(location.href);url.searchParams.set('quality',fine?'fine':'low');
  if(selected>=0)url.searchParams.set('place',places[selected].id);else url.searchParams.delete('place');
  history.replaceState(null,'',url);
}
function updateNotes(){
  const p=places[selected];cards.forEach((b,i)=>b.setAttribute('aria-current',String(i===selected)));
  pins.forEach((b,i)=>b.classList.toggle('active',i===selected));
  $('note-title').textContent=p?p.name+'筆記':'全區筆記';$('description').textContent=p?p.note:homeNote;
  $('scene-kind').textContent=scene?.flat?'平面備援':(p?p.kind:'全區俯瞰');
  $('scene-en').textContent=p?p.en:'Yonghe District';
  const lat=p?.lat??25.009,lon=p?.lon??121.515;
  $('google').href='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(p?lat+','+lon:'新北市永和區');
  $('earth').href='https://earth.google.com/web/@'+lat+','+lon+',12a,'+(p?p.span:3800)+'d,35y,32h,57t,0r';
  writeUrl();
}
function focusPlace(i,animate=true){
  if(!ready)return;selected=i;const p=places[i],[x,y]=world(p.lon,p.lat);
  updateNotes();const pitch=cam.pitch===1?1:(i===2?.87:.68);go({x,y:y-10,angle:cam.angle,pitch,zoom:Math.min(4.9,viewport.clientWidth/p.span)},animate);
}
function overview(animate=true){if(!ready)return;selected=-1;updateNotes();go(homeCamera(),animate);}
let qualityRequest=0;
function qualityButtons(){
  $('fine').setAttribute('aria-pressed',String(fine));$('low').setAttribute('aria-pressed',String(!fine));
  if(scene){
    const d=scene.data;
    $('evidence').textContent=fine?'目前顯示 '+d.nlscFootprints.toLocaleString('zh-TW')+' 筆國土測繪中心衍生建物輪廓，缺口以 OSM 補充。立面、屋頂設備及攤棚為美術示意。':'目前顯示 OSM 建物輪廓與街廓補繪，部分樓高為估計值。';
  }
}
async function quality(value){
  if(!ready)return;
  const id=++qualityRequest;
  const status=$('loading');status.textContent='切換地景精度中…';status.hidden=false;
  try{
    await scene.prepare(value);
    if(id!==qualityRequest)return;
    fine=value;qualityButtons();writeUrl();status.hidden=true;invalidate();
  }catch{
    if(id!==qualityRequest)return;
    status.textContent='圖層未載入，請再點一次精度按鈕。';
  }
}
function clampCenter(){
  const b=scene.data.bounds;cam.x=Math.max(b[0]-120,Math.min(b[2]+120,cam.x));cam.y=Math.max(b[1]-120,Math.min(b[3]+120,cam.y));
}
function zoomBy(factor,x=0,y=0){
  if(!ready)return;tween=null;
  const old=inverse(x,y);cam.zoom=Math.min(6,Math.max(homeScale*.80,cam.zoom*factor));const after=inverse(x,y);
  cam.x+=old[0]-after[0];cam.y+=old[1]-after[1];clampCenter();invalidate();
}
function pan(x,y){if(!ready)return;tween=null;const d=inverse(x,y);cam.x-=d[0];cam.y-=d[1];clampCenter();invalidate();}
function turn(r){if(!ready)return;tween=null;cam.angle+=r;invalidate();}
$('low').onclick=()=>quality(false);$('fine').onclick=()=>quality(true);$('overview').onclick=()=>overview();
$('route').onclick=()=>{showRoute=!showRoute;$('route').setAttribute('aria-pressed',String(showRoute));invalidate();};
$('topdown').onclick=()=>{if(ready){tween=null;cam.pitch=cam.pitch===1?.68:1;invalidate();}};
$('in').onclick=()=>zoomBy(1.45);$('out').onclick=()=>zoomBy(1/1.45);$('left').onclick=()=>turn(-Math.PI/8);$('right').onclick=()=>turn(Math.PI/8);
$('help').onclick=()=>{const panel=$('help-panel');panel.hidden=!panel.hidden;$('help').setAttribute('aria-expanded',String(!panel.hidden));};
viewport.addEventListener('wheel',e=>{
  if(!ready||e.target.closest('#help-panel'))return;e.preventDefault();const r=viewport.getBoundingClientRect();
  zoomBy(Math.exp(-Math.min(100,Math.max(-100,e.deltaY))*.003),e.clientX-r.left-r.width/2,e.clientY-r.top-r.height/2);
},{passive:false});
viewport.addEventListener('pointerdown',e=>{
  if(!ready||e.target.closest('button,#help-panel')||e.button!==0)return;
  tween=null;viewport.focus({preventScroll:true});viewport.setPointerCapture(e.pointerId);touches.set(e.pointerId,[e.clientX,e.clientY]);viewport.classList.add('dragging');
});
viewport.addEventListener('pointermove',e=>{
  const old=touches.get(e.pointerId);if(!old)return;const next=[e.clientX,e.clientY];
  if(touches.size===2){
    const other=[...touches].find(([id])=>id!==e.pointerId)[1],d=p=>Math.hypot(p[0]-other[0],p[1]-other[1]);
    const r=viewport.getBoundingClientRect(),mx=(other[0]+old[0])/2-r.left-r.width/2,my=(other[1]+old[1])/2-r.top-r.height/2;
    if(d(old)>4)zoomBy(d(next)/d(old),mx,my);
    pan((next[0]-old[0])/2,(next[1]-old[1])/2);
  }else if(e.shiftKey)turn((next[0]-old[0])*.009);else pan(next[0]-old[0],next[1]-old[1]);
  touches.set(e.pointerId,next);
});
for(const type of ['pointerup','pointercancel','lostpointercapture'])viewport.addEventListener(type,e=>{touches.delete(e.pointerId);if(!touches.size)viewport.classList.remove('dragging');});
viewport.addEventListener('keydown',e=>{
  if(e.target!==viewport)return;
  const handlers={ArrowLeft:()=>pan(35,0),ArrowRight:()=>pan(-35,0),ArrowUp:()=>pan(0,35),ArrowDown:()=>pan(0,-35),Home:()=>overview(),'+':()=>zoomBy(1.3),'=':()=>zoomBy(1.3),'-':()=>zoomBy(1/1.3),q:()=>turn(-.15),e:()=>turn(.15)};
  if(handlers[e.key]){e.preventDefault();handlers[e.key]();}
});
qualityButtons();
let userWidth=viewport.clientWidth;
new ResizeObserver(()=>{if(ready){const w=viewport.clientWidth;if(w!==userWidth){if(selected<0)go(homeCamera(),false);else homeCamera();userWidth=w;}invalidate();}}).observe(viewport);
try{
  scene=await loadDistrict($('map'),fine);ready=true;qualityButtons();$('loading').hidden=true;go(homeCamera(),false);
  const initial=places.findIndex(p=>p.id===query.get('place'));
  if(initial>=0)focusPlace(initial,false);else updateNotes();
  invalidate();
}catch(error){console.error(error);$('loading').innerHTML='全區地圖載入失敗，<a href="classic.html">開啟原版地景</a>。';}
