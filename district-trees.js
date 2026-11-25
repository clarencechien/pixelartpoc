// A tree is built from horizontal canopy rings. Reuse two models for all park/tree locations.
function canopy(sides,profile){
  const out=[];
  function band(z0,r0,z1,r1,trunk){
    function pt(i,r,z){const a=i*2*Math.PI/sides;return [Math.cos(a)*r,Math.sin(a)*r,z];}
    for(let i=0;i<sides;i++){
      const a=pt(i,r0,z0),b=pt(i+1,r0,z0),c=pt(i+1,r1,z1),d=pt(i,r1,z1);
      const light=(.79+.13*Math.cos(i*2*Math.PI/sides+2.5))*(.87+z1*.16);
      for(const v of [a,b,c,a,c,d])out.push(...v,light,trunk);
    }
  }
  band(0,.13,.35,.13,1);
  for(let i=1;i<profile.length;i++)band(...profile[i-1],...profile[i],0);
  return new Float32Array(out);
}
export function forest(gl,ext,program,project,createBuffer,bytes){
  const vert=`attribute vec3 a_model;attribute vec2 a_tone;attribute vec4 a_tree;attribute vec3 a_leaf;
  varying vec3 v_color;
  ${project}
  void main(){vec4 tree=a_tree*.25;vec3 p=vec3(tree.xy+a_model.xy*tree.z,a_model.z*tree.w);
    v_color=mix(a_leaf,vec3(.53,.46,.34),a_tone.y)*a_tone.x;gl_Position=project(p);}`;
  const frag='precision mediump float;varying vec3 v_color;void main(){gl_FragColor=vec4(v_color,1.);}';
  const obj=program(gl,vert,frag);
  const models=[canopy(5,[[.26,.54],[.56,1],[1,0]]),canopy(8,[[.25,.52],[.43,.93],[.62,1],[.82,.78],[.94,.48],[1,0]])]
    .map(a=>({buffer:createBuffer(gl,a),count:a.length/5}));
  const instances=createBuffer(gl,bytes);
  const [model,tone,tree,leaf]=['a_model','a_tone','a_tree','a_leaf'].map(n=>gl.getAttribLocation(obj.p,n));
  const backup=new DataView(bytes);
  return function drawForest(use,cam,w,h,fine,spans,visible){
    use(obj,cam,w,h);
    const mesh=models[Number(fine && cam.zoom>.42)];
    gl.bindBuffer(gl.ARRAY_BUFFER,mesh.buffer);
    for(const loc of [model,tone])gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(model,3,gl.FLOAT,false,20,0);gl.vertexAttribPointer(tone,2,gl.FLOAT,false,20,12);
    if(ext){
      gl.bindBuffer(gl.ARRAY_BUFFER,instances);
      for(const loc of [tree,leaf]){gl.enableVertexAttribArray(loc);ext.vertexAttribDivisorANGLE(loc,1);}
    }
    for(const [tx,ty,offset,count] of spans){
      if(!visible(tx,ty))continue;
      if(ext){
        gl.vertexAttribPointer(tree,4,gl.SHORT,false,12,offset*12);gl.vertexAttribPointer(leaf,3,gl.UNSIGNED_BYTE,true,12,offset*12+8);
        ext.drawArraysInstancedANGLE(gl.TRIANGLES,0,mesh.count,count);
      }else{
        // WebGL 1 implementations can still place the same mesh with constant attributes.
        for(let i=offset;i<offset+count;i++){
          const n=i*12;
          gl.vertexAttrib4f(tree,backup.getInt16(n,true),backup.getInt16(n+2,true),backup.getInt16(n+4,true),backup.getInt16(n+6,true));
          gl.vertexAttrib3f(leaf,backup.getUint8(n+8)/255,backup.getUint8(n+9)/255,backup.getUint8(n+10)/255);
          gl.drawArrays(gl.TRIANGLES,0,mesh.count);
        }
      }
    }
    if(ext)for(const loc of [tree,leaf]){ext.vertexAttribDivisorANGLE(loc,0);gl.disableVertexAttribArray(loc);}
    for(const loc of [model,tone])gl.disableVertexAttribArray(loc);
  };
}
