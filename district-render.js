import {forest} from './district-trees.js';
// The mesh, ground and landmark slices share one local east/south/up coordinate system, in metres.
const projectSource = `
uniform vec2 u_center;
uniform vec2 u_pixels;
uniform vec2 u_turn;
uniform float u_zoom;
uniform vec2 u_pitch;
vec4 project(vec3 p){
  vec2 d=p.xy-u_center;
  float right=dot(d,vec2(u_turn.x,-u_turn.y));
  float front=dot(d,vec2(u_turn.y,u_turn.x));
  return vec4(2.*right*u_zoom/u_pixels.x, -2.*(u_pitch.x*front-u_pitch.y*p.z)*u_zoom/u_pixels.y,
              -(u_pitch.y*front+u_pitch.x*p.z)/8000.,1.);
}`;
const sceneVertex = `attribute vec3 a_pos;
attribute vec3 a_color;
attribute vec3 a_style;
varying vec3 v_color;
varying vec3 v_world;
varying vec3 v_style;
${projectSource}
void main(){v_world=a_pos*.25;v_color=a_color;v_style=a_style;gl_Position=project(v_world);}`;
const sceneFragment = `precision highp float;
varying vec3 v_color; varying vec3 v_world; varying vec3 v_style;
uniform float u_detail;
uniform sampler2D u_signs;
uniform float u_zoom;
void main(){
  vec3 c=v_color;
  float mat=v_style.x;
  if(mat>5.5){gl_FragColor=texture2D(u_signs,v_style.yz/255.);return;}
  float strength=smoothstep(.38,1.15,u_zoom);
  if(mat>.5 && mat<1.5 && strength>.0){
    float angle=v_style.y*.02463994;
    float x=dot(v_world.xy,vec2(cos(angle),sin(angle)))+v_style.z*.62;
    float facade=floor(x*2.)*.5;
    float level=mod(v_world.z,3.15);
    float bay=mod(facade,3.6);
    if(level>1.05 && level<2.55 && bay>.65 && bay<2.75)
      c=mix(c,vec3(.32,.44,.44),(.50+.21*u_detail)*strength);
    if(u_detail>.5 && level>.15 && level<.52)c*=1.-.19*strength;
    if(u_detail>.5 && level>2.45 && level<2.80 && bay<2.98)c=mix(c,vec3(.85,.82,.70),.41*strength);
    if(u_detail>.5 && bay>1.6 && bay<1.90 && level>1.2 && level<2.45)c*=1.+.23*strength;
  }
  if(mat>2.5 && mat<3.5 && u_detail>.5){c*=1.-.085*strength*step(1.45,mod(floor(v_world.x*1.4),2.));}
  if(mat>3.5 && strength>.0){
    float angle=v_style.y*.02463994;
    float facade=dot(v_world.xy,vec2(cos(angle),sin(angle)))+v_style.z*.37;
    float x=floor(facade*4.)*.25, z=floor(v_world.z*4.)*.25;
    vec3 finish=c;
    if(mat<4.5){
      float floorY=mod(z,3.25), bay=mod(x,3.80);
      if(floorY<.34)finish*=.84;
      if(bay>.52 && bay<3.14 && floorY>.89 && floorY<2.68){
        finish=vec3(.71,.70,.58);
        if(bay>.74 && bay<2.96 && floorY>1.09 && floorY<2.55){
          float glazing=fract(sin(dot(vec2(floor(x/3.8),floor(z/3.25)),vec2(23.7,19.3)))*257.);
          finish=mix(vec3(.21,.32,.32),vec3(.48,.64,.64),glazing);
          if(bay>1.71 && bay<1.95)finish=vec3(.65,.68,.60);
        }
      }
      if(z<2.8 && bay>.46)finish=mix(vec3(.19,.26,.25),vec3(.51,.49,.38),step(.58,fract(z*1.7)));
    }else{
      float pane=mod(x,2.8), storey=mod(z,3.4);
      finish=mix(c,vec3(.36,.63,.68),.33+.20*sin(floor(x/2.8)*.71+floor(z/3.4)*.17));
      if(storey<.55)finish*=.61;
      if(pane<.28 || (storey>.56 && storey<.8))finish=mix(finish,vec3(.75,.77,.65),.65);
    }
    c=mix(c,finish,strength);
  }
  gl_FragColor=vec4(c,1.);
}`;
const groundVertex = `attribute vec2 a_xy;uniform vec4 u_bounds;varying vec2 v_uv;
${projectSource}
void main(){v_uv=a_xy;gl_Position=project(vec3(mix(u_bounds.xy,u_bounds.zw,a_xy),-.12));}`;
const groundFragment = `precision mediump float;varying vec2 v_uv;uniform sampler2D u_tex;
void main(){vec4 c=texture2D(u_tex,v_uv);if(c.a<.5)discard;gl_FragColor=vec4(c.rgb,1.);}`;

function program(gl,vert,frag){
  const p=gl.createProgram();
  for(const [type,source] of [[gl.VERTEX_SHADER,vert],[gl.FRAGMENT_SHADER,frag]]){
    const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);
    if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));
    gl.attachShader(p,s);gl.deleteShader(s);
  }
  gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));
  const uniforms={};for(const n of ['center','pixels','turn','zoom','detail','bounds','tex','pitch','signs'])uniforms[n]=gl.getUniformLocation(p,'u_'+n);
  return {p,uniforms};
}
function createBuffer(gl,bytes){
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,bytes,gl.STATIC_DRAW);return b;
}
function imageAt(url){
  return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error(url));img.src=url;});
}
export async function loadDistrict(canvas,initialFine){
  const root=new URL('city/',import.meta.url);
  const response=await fetch(new URL('district.json',root));if(!response.ok)throw Error('District data');
  const data=await response.json();
  const ground=await imageAt(new URL('ground-fine.png',root));
  const flatView=async()=>planar(canvas,data,[ground,await imageAt(new URL('ground-streetscape.png',root))]);
  let gl=canvas.getContext('webgl',{alpha:true,antialias:false,depth:true,powerPreference:'high-performance',preserveDrawingBuffer:false});
  if(!gl||!window.DecompressionStream)return flatView();
  try{
    const world=program(gl,sceneVertex,sceneFragment),surface=program(gl,groundVertex,groundFragment);
    const buffers=new Map(),pending=new Map();
    async function loadMesh(name){
      const spans=data.meshes[name];
      const result=await fetch(new URL(name+'.mesh.gz',root));if(!result.ok)throw Error('District mesh: '+name);
      let packed=await result.arrayBuffer();
      if(new Uint8Array(packed)[0]===31)packed=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
      const last=spans.at(-1);if(packed.byteLength!==data.stride*(last[3]+last[4]))throw Error('Incomplete mesh');
      buffers.set(name,createBuffer(gl,packed));
    }
    function ensure(name){
      if(buffers.has(name))return Promise.resolve();
      if(!pending.has(name))pending.set(name,loadMesh(name).finally(()=>pending.delete(name)));
      return pending.get(name);
    }
    let signTexture,signRequest;
    function prepareSigns(){
      if(!signRequest)signRequest=imageAt(new URL('signs.png',root)).then(img=>{signTexture=texture(img);})
        .catch(err=>{signRequest=null;throw err;});
      return signRequest;
    }
    const prepare=fine=>fine?Promise.all([ensure('streetscape'),prepareSigns()]):Promise.all([ensure('fine'),ensure('baseline-props')]);
    const treeData=fetch(new URL('trees.bin',root)).then(r=>{if(!r.ok)throw Error('Tree instances');return r.arrayBuffer();});
    const [,,trees]=await Promise.all([ensure('shared'),prepare(initialFine),treeData]);
    const drawTrees=forest(gl,gl.getExtension('ANGLE_instanced_arrays'),program,projectSource,createBuffer,trees);
    const plane=createBuffer(gl,new Float32Array([0,0,1,0,1,1,0,0,1,1,0,1]));
    function texture(img){
      const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.NEAREST);
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
      if(img.width>gl.getParameter(gl.MAX_TEXTURE_SIZE)||img.height>gl.getParameter(gl.MAX_TEXTURE_SIZE)){
        const half=document.createElement('canvas');half.width=img.width>>1;half.height=img.height>>1;
        half.getContext('2d').drawImage(img,0,0,half.width,half.height);img=half;
      }
      gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);return t;
    }
    const groundTexture=texture(ground);
    function use(obj,cam,w,h){
      const u=obj.uniforms;gl.useProgram(obj.p);gl.uniform2f(u.center,cam.x,cam.y);gl.uniform2f(u.pixels,w,h);
      gl.uniform2f(u.turn,Math.cos(cam.angle),Math.sin(cam.angle));gl.uniform1f(u.zoom,cam.zoom);gl.uniform2f(u.pitch,cam.pitch,Math.sqrt(1-cam.pitch**2));
      return u;
    }
    function attribute(p,name,size,type,normalized,stride,offset){
      const loc=gl.getAttribLocation(p,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,type,normalized,stride,offset);return loc;
    }
    function draw(cam,w,h,fine){
      resize(canvas,w,h);gl.viewport(0,0,canvas.width,canvas.height);
      gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);
      const surfaceU=use(surface,cam,w,h);gl.uniform4fv(surfaceU.bounds,data.bounds);
      gl.bindBuffer(gl.ARRAY_BUFFER,plane);const xy=attribute(surface.p,'a_xy',2,gl.FLOAT,false,0,0);
      gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,groundTexture);gl.drawArrays(gl.TRIANGLES,0,6);gl.disableVertexAttribArray(xy);
      const u=use(world,cam,w,h);gl.uniform1f(u.detail,1);
      gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,signTexture||groundTexture);gl.uniform1i(u.signs,1);gl.activeTexture(gl.TEXTURE0);
      const c=Math.cos(cam.angle),s=Math.sin(cam.angle);
      function visible(tx,ty){
        const x=(tx+.5)*256-cam.x,y=(ty+.5)*256-cam.y;
        return Math.abs(x*c-y*s)*cam.zoom<w/2+470*cam.zoom && Math.abs((x*s+y*c)*cam.pitch)*cam.zoom<h/2+460*cam.zoom;
      }
      for(const name of (fine?['shared','streetscape']:['shared','baseline-props','fine'])){
        gl.bindBuffer(gl.ARRAY_BUFFER,buffers.get(name));
        const attrs=[attribute(world.p,'a_pos',3,gl.SHORT,false,12,0),attribute(world.p,'a_color',3,gl.UNSIGNED_BYTE,true,12,6),attribute(world.p,'a_style',3,gl.UNSIGNED_BYTE,false,12,9)];
        for(const [detail,tx,ty,start,count] of data.meshes[name]){
          if(detail && cam.zoom<.26)continue;
          if(!visible(tx,ty))continue;
          gl.drawArrays(gl.TRIANGLES,start,count);
        }
        attrs.forEach(i=>gl.disableVertexAttribArray(i));
      }
      drawTrees(use,cam,w,h,fine,data.treeCells,visible);
    }
    return {data,draw,prepare,flat:false};
  }catch(error){console.warn('Using flat district view',error);return flatView();}
}
function resize(canvas,w,h){
  const cw=Math.max(1,Math.round(w)),ch=Math.max(1,Math.round(h));
  if(canvas.width!==cw||canvas.height!==ch){canvas.width=cw;canvas.height=ch;}
}
function planar(canvas,data,images){
  // A canvas with an existing WebGL context cannot switch context type.
  const fallback=canvas.cloneNode(false);canvas.replaceWith(fallback);
  const ctx=fallback.getContext('2d');
  function draw(cam,w,h,fine){
    resize(fallback,w,h);const rx=fallback.width/w,ry=fallback.height/h;
    ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,fallback.width,fallback.height);
    const c=Math.cos(cam.angle),s=Math.sin(cam.angle),k=cam.zoom,b=data.bounds;
    ctx.setTransform(k*c*rx,k*s*cam.pitch*ry,-k*s*rx,k*c*cam.pitch*ry,
      rx*(w/2-k*(cam.x*c-cam.y*s)),ry*(h/2-k*cam.pitch*(cam.x*s+cam.y*c)));
    ctx.imageSmoothingEnabled=false;ctx.drawImage(images[Number(fine)],b[0],b[1],b[2]-b[0],b[3]-b[1]);
  }
  return {data,draw,prepare:async()=>{},flat:true};
}
