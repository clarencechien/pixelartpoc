const get = id => document.getElementById(id);
const slider = get('station');
const canvas = get('profile');
const ctx = canvas.getContext('2d');
const buttons = [...get('presets').querySelectorAll('button')];
let model, solids, request, onMove, frame = 0;

// Every solid is a pair of matching convex rings, or one open polygon for a thin surface.
function unpack([bridge, face, coords]) {
  const points = [];
  for (let i = 0; i < coords.length; i += 3) points.push(coords.slice(i, i + 3).map(v => v / 4));
  const count = face ? points.length : points.length / 2;
  const edges = [];
  for (let i = 0; i < count; i++) {
    const next = (i + 1) % count;
    edges.push([points[i], points[next]]);
    if (!face) edges.push([points[i + count], points[next + count]], [points[i], points[i + count]]);
  }
  return {bridge, edges, minY:Math.min(...points.map(p => p[1])), maxY:Math.max(...points.map(p => p[1]))};
}

function hull(points) {
  const sorted = points.sort((a,b) => a[0]-b[0] || a[1]-b[1])
    .filter((p,i,all) => !i || p[0]!==all[i-1][0] || p[1]!==all[i-1][1]);
  if (sorted.length < 3) return sorted;
  function chain(rows) {
    const path = [];
    for (const p of rows) {
      while (path.length >= 2) {
        const [a,b] = path.slice(-2);
        if ((b[0]-a[0])*(p[1]-a[1]) - (b[1]-a[1])*(p[0]-a[0]) > 1e-8) break;
        path.pop();
      }
      path.push(p);
    }
    return path.slice(0,-1);
  }
  return chain(sorted).concat(chain(sorted.reverse()));
}

function intersect(solid, y) {
  const hits = [];
  for (const [a,b] of solid.edges) {
    if (a[1]===y) hits.push([a[0],a[2]]);
    if ((a[1]<y && b[1]>y) || (a[1]>y && b[1]<y)) {
      const t = (y-a[1])/(b[1]-a[1]);
      hits.push([a[0]+t*(b[0]-a[0]), a[2]+t*(b[2]-a[2])]);
    }
    if (b[1]===y) hits.push([b[0],b[2]]);
  }
  return hull(hits);
}

function draw() {
  frame = 0;
  if (!model || !canvas.clientWidth) return;
  const distance = slider.valueAsNumber, y = model.south-distance;
  const cuts = [];
  for (const solid of solids) {
    if (y < solid.minY || y > solid.maxY) continue;
    const ring = intersect(solid,y);
    if (ring.length) cuts.push({ring,bridge:solid.bridge});
  }
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const ratio = Math.min(3, window.devicePixelRatio || 1);
  canvas.width = Math.round(w*ratio); canvas.height = Math.round(h*ratio);
  ctx.setTransform(ratio,0,0,ratio,0,0);
  const left = w<320 ? 28 : 42, right = w-9;
  const base = h-22;
  const xs = cuts.flatMap(c=>c.ring.map(p=>p[0]));
  const center = (Math.min(...xs)+Math.max(...xs))/2;
  const scale = Math.min((right-left)/Math.max(90,Math.max(...xs)-Math.min(...xs)+8), (base-25)/56);
  const X = x => (left+right)/2+(x-center)*scale;
  const Z = z => base-z*scale;
  ctx.font = '12px sans-serif';
  ctx.fillStyle = '#526858'; ctx.textAlign = 'left';
  ctx.fillText('相對高度 (m)', 7, 16);
  for (let z=0; z<=50; z+=10) {
    ctx.strokeStyle = z===0?'#80998b':'#e3e7d9';
    ctx.beginPath();ctx.moveTo(left,Z(z));ctx.lineTo(right,Z(z));ctx.stroke();
    ctx.fillStyle='#596d61';ctx.textAlign='right';ctx.fillText(String(z),left-5,Z(z)+4);
  }
  const names = ['新中正橋','川端橋'], colors = ['#3e7669','#ac603e'];
  const deckRange = [[],[]];
  let pier = false, footing = false, hanger = false;
  for (const {ring,bridge} of cuts) {
    const zs = ring.map(p=>p[1]), low = Math.min(...zs), high = Math.max(...zs);
    if (bridge===1 && low<2 && high>3) pier=true;
    if (bridge===1 && low<1) footing=true;
    if (bridge===0 && low<13 && high>20) hanger=true;
    if (low<10 && high>8) deckRange[bridge].push(...ring.map(p=>p[0]));
    ctx.fillStyle=colors[bridge];ctx.strokeStyle=colors[bridge];ctx.lineWidth=1;
    ctx.beginPath();
    ring.forEach(([x,z],i)=>i?ctx.lineTo(X(x),Z(z)):ctx.moveTo(X(x),Z(z)));
    if (ring.length>2) {ctx.closePath();ctx.fill();}
    ctx.stroke();
  }
  ctx.textAlign='center';
  for (let i=0;i<2;i++) {
    const points = deckRange[i];
    if (!points.length) continue;
    const mid = (Math.min(...points)+Math.max(...points))/2;
    ctx.fillStyle = colors[i];ctx.fillText(names[i],X(mid),h-5);
  }
  const oldBridge = pier ? '這一刀穿過川端橋的雙柱橋墩。'
    : footing ? '這一刀擦過川端橋橋墩底座的邊緣。' : '川端橋橋面下方是兩座橋墩之間的空間。';
  const reading = oldBridge +
    (hanger?'新中正橋的吊索在這裡接上橋面。':'橋面上方的綠色截面是新中正橋的拱肋。');
  if (get('reading').textContent !== reading) get('reading').textContent=reading;
  canvas.setAttribute('aria-label','自永和側起點 '+distance+' 公尺。'+reading);
}

function update(distance) {
  slider.value=String(distance);
  const d=slider.valueAsNumber;
  onMove();
  const value='距起點 '+d+' m';
  get('chainage').value=value;slider.setAttribute('aria-valuetext','距永和側起點 '+d+' 公尺');
  for (let i=0;i<buttons.length;i++) buttons[i].setAttribute('aria-pressed',String(d===model.presets[i]));
  if (!frame) frame=requestAnimationFrame(draw);
}

slider.addEventListener('input',()=>update(slider.valueAsNumber));
new ResizeObserver(()=>{if(model && !frame) frame=requestAnimationFrame(draw);}).observe(canvas);

async function load() {
  const response=await fetch('city/bridge-section.json');
  if (!response.ok) throw Error('Section data '+response.status);
  model=await response.json();
  solids=model.solids.map(unpack);
  slider.max=String(model.south-model.north);
  return {
    extent:model.extent,
    get y(){return model.south-slider.valueAsNumber;},
    moveTo(y){update(Math.round((model.south-y)*4)/4);},
    enable(){
      slider.disabled=false;
      buttons.forEach((button,i)=>{button.disabled=false;button.onclick=()=>update(model.presets[i]);});
      update(slider.dataset.visited ? slider.valueAsNumber : model.presets[0]);
      slider.dataset.visited='true';
    }
  };
}
export function prepareSection(moveLine) {
  onMove=moveLine;
  if (!request) request=load().catch(error=>{request=null;throw error;});
  return request;
}
