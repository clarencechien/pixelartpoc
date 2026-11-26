import {prepareSection} from './bridge-section.js?v=map';
import {loadDistrict} from './district-render.js?v=walk';

const places=[
  {id:'bridge',pitch:.67,angle:-1.02,lift:25,name:'中正橋',en:'Zhongzheng Bridge',kind:'河岸地標',lon:121.51555,lat:25.02012,z:49,span:310,note:'白色橋拱跨過新店溪。往南平移越過河濱，再沿永和路走，就是頂溪站。'},
  {id:'dingxi',pitch:.67,angle:.98,lift:6,name:'頂溪站',en:'Dingxi Station',kind:'捷運街角',lon:121.515482,lat:25.014196,z:7,span:70,note:'永和路二段 233 號的二號出口嵌在沿街大樓的一樓。往站名牌下方看，可以找到騎樓裡的入口和階梯。'},
  {id:'lehua',pitch:.75,angle:1.20,lift:6,name:'樂華夜市',en:'Lehua Night Market',kind:'夜市街區',lon:121.51399,lat:25.00867,z:8.7,span:98,note:'永平路上的彩色棚架沿街彎進街區。沿路找夜市入口的紅底招牌、斜面遮棚和攤前的燈籠。'},
  {id:'baofu',pitch:.59,angle:-.42,lift:11,name:'保福宮',en:'Baofu Temple',kind:'寺廟建築',lon:121.50864028,lat:25.01319537,z:23,span:118,note:'從仁愛路看進廟埕，屋簷前低後高。旋轉鏡頭，可以看到三進廟殿的層次、上翹的屋脊、廊柱和簷下燈籠。'},
  {id:'kawabata',pitch:.50,angle:.89,lift:8,name:'川端橋',en:'Kawabata Bridge',kind:'歷史橋梁',lon:121.51605,lat:25.02027,z:10,span:162,note:'新中正橋上游側的川端橋保留了鋼板梁與雙柱拱形橋墩。特色版可近看兩座橋並排跨河，以及舊橋步道兩側的復古欄杆。'},
  {id:'renai',pitch:.79,angle:-.32,lift:0,name:'仁愛公園',en:'Ren’ai Park',kind:'城市公園',lon:121.50624,lat:25.01117,z:2,span:390,note:'環形步道繞著中央草坪，西南側的音樂台面向扇形觀眾席。點選園內設施，可以近看溜冰場的跑道、音樂台的階梯座位，或遊戲場的城堡滑梯。'}
];
const $=id=>document.getElementById(id);
const viewport=$('viewport'),cam={x:0,y:0,angle:-.45,zoom:1,pitch:.68};
const homeNote=$('description').textContent;
const query=new URLSearchParams(location.search);
let fine=query.get('quality')!=='low',selected=-1,showRoute=false,routeOverview=false,returnView=null,scene,tween,frame,homeScale=.15,ready=false;
let sectionSession=null;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const pins=[],cards=[],touches=new Map();
const svgNS='http://www.w3.org/2000/svg';
const lines=document.createElementNS(svgNS,'svg');
lines.id='journey';lines.style.display='none';lines.setAttribute('aria-hidden','true');lines.classList.add('journey');viewport.insertBefore(lines,$('pins'));
const paths=[0,1].map(()=>{
  const path=document.createElementNS(svgNS,'path'),halo=document.createElementNS(svgNS,'path');
  halo.classList.add('halo');lines.append(halo,path);return [halo,path];
});
places.forEach((p,i)=>{
  const num=String(i+1).padStart(2,'0');
  const btn=document.createElement('button');btn.className='place';
  btn.innerHTML='<span class="thumb"><img alt="" src="assets/'+p.id+'-icon.png"></span><span class="place-copy"><strong>'+p.name+'</strong><small>'+p.en+'</small></span><span class="idx">'+num+'</span>';
  btn.onclick=()=>focusPlace(i);$('places').append(btn);cards.push(btn);
  const pin=document.createElement('button');pin.hidden=true;pin.className='map-pin';pin.setAttribute('aria-label','前往'+p.name);
  pin.innerHTML='<span>'+num+'</span>'+p.name;pin.onclick=()=>focusPlace(i);$('pins').append(pin);pins.push(pin);
});
function setLabels(visible){
  $('labels').setAttribute('aria-pressed',String(visible));
  $('pins').hidden=!visible;
}
setLabels(query.get('labels')!=='off');
$('labels').onclick=()=>{
  setLabels($('pins').hidden);
  writeUrl();
};
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
  scene.draw(cam,w,h,sectionSession?.data ? true : fine);
  placeCutLine();
  const placed=[];
  places.forEach((place,i)=>{
    const [x,y]=project(...world(place.lon,place.lat),scene.flat?0:place.z);
    let lift=12;for(const prior of placed)if(Math.abs(prior[0]-x)<85 && Math.abs(prior[1]-(y-lift))<27)lift+=28;
    placed.push([x,y-lift]);const pin=pins[i];
    pin.hidden=(sectionSession && i!==0 && i!==4)||(!sectionSession && routeOverview && i>2)||x<12||x>w-12||y<23||y>h+3;pin.style.left=x+'px';pin.style.top=(y-lift)+'px';pin.style.setProperty('--stem',(lift-3)+'px');
  });
  lines.style.display=showRoute&&!sectionSession?'':'none';
  if(showRoute&&!sectionSession)scene.data.route.forEach((segment,i)=>{
    const d=segment.map(([x,y],j)=>{
      const onBridge=i===0 && y<world(121.5156,25.0176)[1];
      const [a,b]=project(x,y,scene.flat?0:(onBridge?10:.4));
      return (j?'L':'M')+a.toFixed(1)+' '+b.toFixed(1);
    }).join(' ');
    for(const path of paths[i])path.setAttribute('d',d);
  });
  $('needle').style.transform='rotate('+Math.atan2(Math.sin(cam.angle),Math.cos(cam.angle)*cam.pitch)+'rad)';
  const meters=[5,10,20,50,100,200,500,1000].find(m=>m*cam.zoom>=28)??1000;
  $('scale').textContent=meters+' m';$('scale').style.setProperty('--bar',Math.round(meters*cam.zoom)+'px');
  const d=scene.data;$('coords').textContent=(d.origin[1]+cam.y/d.metersPerDegree[1]).toFixed(5)+'° N  '+(d.origin[0]+cam.x/d.metersPerDegree[0]).toFixed(5)+'° E';
  $('topdown').setAttribute('aria-pressed',String(cam.pitch===1));
  $('out').disabled=cam.zoom<=homeScale*.81;$('in').disabled=cam.zoom>=13.99;
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
  if(selected>=0)url.searchParams.set('place',places[selected].id);else url.searchParams.set('place',routeOverview?'route':'all');
  if(sectionSession)url.searchParams.set('section','bridges');else url.searchParams.delete('section');
  if($('pins').hidden)url.searchParams.set('labels','off');else url.searchParams.delete('labels');
  history.replaceState(null,'',url);
}
function sectionCamera() {
  const [west,north,east,south]=sectionSession.data.extent;
  const angle=-.18, pitch=.8;
  const width=(east-west)*Math.cos(angle)+(south-north)*Math.abs(Math.sin(angle));
  const height=((east-west)*Math.abs(Math.sin(angle))+(south-north)*Math.cos(angle))*pitch+32;
  return {x:(west+east)/2,y:(north+south)/2-10,angle,pitch,
    zoom:Math.min(viewport.clientWidth*.88/width,viewport.clientHeight*.83/height)};
}
function placeCutLine() {
  const data=sectionSession?.data;
  if(!data)return;
  const [west,,east]=data.extent, z=scene.flat?0:10;
  const [ax,ay]=project(west,data.y,z),[bx,by]=project(east,data.y,z);
  const style=$('cut-line').style;
  style.left=ax+'px';style.top=ay+'px';style.width=Math.hypot(bx-ax,by-ay)+'px';
  style.transform='rotate('+Math.atan2(by-ay,bx-ax)+'rad)';
}
async function openSection() {
  if(!ready || sectionSession)return;
  const session={camera:{...(tween?.to??cam)},data:null};
  sectionSession=session;tween=null;qualityRequest++;
  touches.clear();viewport.classList.remove('dragging');
  $('loading').hidden=true;
  $('section-panel').hidden=false;document.body.classList.add('section-open');
  userSize=[viewport.clientWidth,viewport.clientHeight].join();
  $('overview').textContent='雙橋全景';
  $('section-toggle').setAttribute('aria-expanded','true');$('section-toggle').textContent='關閉剖面';
  $('pins').inert=true;$('station').disabled=true;
  for(const button of $('presets').children)button.disabled=true;
  $('reading').textContent='正在載入雙橋模型…';writeUrl();
  try{
    const [data]=await Promise.all([prepareSection(placeCutLine),scene.prepare(true)]);
    if(sectionSession!==session)return;
    session.data=data;go(sectionCamera(),false);
    $('cut-line').hidden=false;data.enable();
  }catch(error){
    if(sectionSession!==session)return;
    console.warn(error);$('reading').textContent='雙橋模型載入失敗。';
    const retry=document.createElement('button');retry.textContent='再試一次';
    retry.onclick=()=>{closeSection();openSection();};$('reading').append(retry);
  }
}
function closeSection() {
  if(!sectionSession)return;
  const {camera}=sectionSession;sectionSession=null;cutDrag=null;
  document.body.classList.remove('section-open');$('section-panel').hidden=true;$('cut-line').hidden=true;
  $('pins').inert=false;$('section-toggle').setAttribute('aria-expanded','false');$('section-toggle').textContent='雙橋剖面';
  userSize=[viewport.clientWidth,viewport.clientHeight].join();
  $('overview').textContent='全區';go(camera,false);writeUrl();$('section-toggle').focus({preventScroll:true});
}
$('section-toggle').onclick=()=>sectionSession?closeSection():openSection();
document.addEventListener('keydown',e=>{if(sectionSession && e.key==='Escape')closeSection();});
let cutDrag=null;
const cutLine=$('cut-line');
cutLine.addEventListener('pointerdown',e=>{
  if(!sectionSession?.data || !e.isPrimary || e.button!==0)return;
  e.stopPropagation();cutLine.setPointerCapture(e.pointerId);
  cutDrag={id:e.pointerId,x:e.clientX,y:e.clientY,worldY:sectionSession.data.y};
});
cutLine.addEventListener('pointermove',e=>{
  if(cutDrag?.id!==e.pointerId)return;
  const [,dy]=inverse(e.clientX-cutDrag.x,e.clientY-cutDrag.y);
  sectionSession.data.moveTo(cutDrag.worldY+dy);
});
cutLine.addEventListener('lostpointercapture',()=>{cutDrag=null;});
function updateNotes(){
  const p=places[selected];cards.forEach((b,i)=>b.setAttribute('aria-current',String(i===selected)));
  pins.forEach((b,i)=>b.classList.toggle('active',i===selected));
  $('note-title').textContent=p?p.name+'筆記':'全區筆記';$('description').textContent=p?p.note:homeNote;
  $('park-stops').hidden=p?.id!=='renai';
  if(routeOverview){$('note-title').textContent='三站走讀線';$('description').textContent='從中正橋沿永和路經過頂溪站，再轉往樂華夜市，全長約 1.37 公里。點地圖上的站名可近看街景。';}
  $('scene-kind').textContent=scene?.flat?'平面備援':(p?p.kind:(routeOverview?'三站走讀線':'全區俯瞰'));
  $('scene-en').textContent=p?p.en:(routeOverview?'Yonghe Walk':'Yonghe District');
  const lat=p?.lat??25.009,lon=p?.lon??121.515;
  $('google').href='https://www.google.com/maps/search/?api=1&query='+encodeURIComponent(p?lat+','+lon:'新北市永和區');
  $('earth').href='https://earth.google.com/web/@'+lat+','+lon+',12a,'+(p?p.span:3800)+'d,35y,32h,57t,0r';
  writeUrl();
}
function focusPlace(i,animate=true){
  if(!ready)return;
  if(sectionSession)closeSection();
  const keepTopdown=cam.pitch===1 && !routeOverview;
  routeOverview=false;returnView=null;selected=i;const p=places[i],[x,y]=world(p.lon,p.lat);
  updateNotes();
  const pitch=keepTopdown?1:p.pitch;
  const angle=p.angle;
  const lift=p.lift*Math.sqrt(1-pitch*pitch)/pitch;
  go({x:x-Math.sin(angle)*lift,y:y-Math.cos(angle)*lift,angle,pitch,zoom:Math.min(12,viewport.clientWidth/p.span)},animate);
}
function overview(animate=true){
  if(!ready)return;
  if(sectionSession){if(sectionSession.data)go(sectionCamera(),animate);return;}
  routeOverview=false;returnView=null;selected=-1;updateNotes();go(homeCamera(),animate);
}
let qualityRequest=0;
function qualityButtons(){
  $('fine').setAttribute('aria-pressed',String(fine));$('low').setAttribute('aria-pressed',String(!fine));
  if(scene){
    const d=scene.data;
    $('evidence').textContent='兩版共用 '+d.nlscFootprints.toLocaleString('zh-TW')+' 筆國土測繪中心衍生輪廓及 OSM 補圖。'+(fine?'特色版以像素造型詮釋廟宇、街屋和地標，立面及屋頂細節為美術示意。':'低精度基準沿用上一版高精度的建物和街景。');
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
  const old=inverse(x,y);cam.zoom=Math.min(14,Math.max(homeScale*.80,cam.zoom*factor));const after=inverse(x,y);
  cam.x+=old[0]-after[0];cam.y+=old[1]-after[1];clampCenter();invalidate();
}
function pan(x,y){if(!ready)return;tween=null;const d=inverse(x,y);cam.x-=d[0];cam.y-=d[1];clampCenter();invalidate();}
function turn(r){if(!ready)return;tween=null;cam.angle+=r;invalidate();}
$('low').onclick=()=>quality(false);$('fine').onclick=()=>quality(true);$('overview').onclick=()=>overview();
function routeCamera(){
  const points=scene.data.route.flat(),xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const west=Math.min(...xs),east=Math.max(...xs),north=Math.min(...ys),south=Math.max(...ys);
  const zoom=Math.min((viewport.clientWidth-108)/(east-west),(viewport.clientHeight-154)/(south-north));
  return {x:(west+east)/2,y:(north+south)/2,angle:0,pitch:1,zoom:Math.max(.05,zoom)};
}
function toggleRoute(animate=true){
  if(!ready)return;
  showRoute=!showRoute;
  $('route').setAttribute('aria-pressed',String(showRoute));
  $('route').textContent=showRoute?'隱藏走讀線':'顯示走讀線';
  if(showRoute){
    returnView={camera:{...cam},selected};
    routeOverview=true;selected=-1;go(routeCamera(),animate);
  }else if(routeOverview){
    routeOverview=false;selected=returnView?.selected??-1;
    go(returnView?.camera??homeCamera(),animate);returnView=null;
  }
  updateNotes();invalidate();
}
$('route').onclick=()=>toggleRoute();
for(const [name,lon,lat,span] of [['露天音樂台',121.50560,25.01078,108],['溜冰場',121.505683,25.01157,116],['城堡遊戲場',121.506986,25.012221,65]]){
  const button=document.createElement('button');button.textContent=name;
  button.onclick=()=>{const [x,y]=world(lon,lat);go({x,y,angle:name==='露天音樂台'?2.15:-.32,pitch:.63,zoom:Math.min(12,viewport.clientWidth/span)},true);};
  $('park-stops').append(button);
}
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
let userSize=[viewport.clientWidth,viewport.clientHeight].join();
new ResizeObserver(()=>{if(ready){const size=[viewport.clientWidth,viewport.clientHeight].join();if(size!==userSize){const home=homeCamera();if(sectionSession?.data)go(sectionCamera(),false);else if(!sectionSession && routeOverview)go(routeCamera(),false);else if(!sectionSession && selected<0)go(home,false);userSize=size;}invalidate();}}).observe(viewport);
try{
  scene=await loadDistrict($('map'),fine);ready=true;$('section-toggle').disabled=false;$('route').disabled=false;qualityButtons();$('loading').hidden=true;go(homeCamera(),false);
  const initial=places.findIndex(p=>p.id===query.get('place'));
  if(initial>=0)focusPlace(initial,false);else if(query.get('place')==='route')toggleRoute(false);else if(query.get('place')==='all')updateNotes();else focusPlace(3,false);
  if(query.get('section')==='bridges')openSection();
  invalidate();
}catch(error){console.error(error);$('loading').textContent='地圖載入失敗。';const retry=document.createElement('button');retry.textContent='重新載入';retry.onclick=()=>location.reload();$('loading').append(retry);}
