// With a site-restricted browser key, the same landmark opens in an embedded Google 3D map.
(() => {
  const key=document.querySelector('meta[name="google-maps-browser-key"]').content.trim();
  if(!key)return;
  const link=get('earth'), dialog=get('real-dialog'), host=get('real-map'), status=get('real-status');
  let library, viewId=0;
  function mapsLibrary(){
    if(window.google?.maps?.importLibrary)return google.maps.importLibrary('maps3d');
    if(library)return library;
    library=new Promise((resolve,reject)=>{
      const script=document.createElement('script');
      const finish=()=>{clearTimeout(timer);delete window.atlasMapsReady;};
      const fail=()=>{finish();script.remove();reject(Error('Maps unavailable'));};
      const timer=setTimeout(fail,18000);
      window.atlasMapsReady=()=>{finish();google.maps.importLibrary('maps3d').then(resolve,reject);};
      script.onerror=fail;
      script.src='https://maps.googleapis.com/maps/api/js?'+new URLSearchParams({key,v:'weekly',loading:'async',language:'zh-TW',region:'TW',callback:'atlasMapsReady'});
      document.head.append(script);
    }).catch(error=>{library=null;throw error;});
    return library;
  }
  link.textContent='Google Maps 3D 實景';
  link.onclick=async event=>{
    if(event.metaKey||event.ctrlKey||event.shiftKey||event.altKey)return;
    event.preventDefault();
    const id=++viewId,place=places[active];
    get('real-title').textContent=place.name+' · Google Maps 3D';
    get('earth-fallback').href=link.href;
    host.replaceChildren();status.textContent='載入 Google 立體實景中…';dialog.showModal();
    const failed=()=>{if(id===viewId){host.replaceChildren();status.textContent='目前無法載入 Google Maps 3D，可在 Google 地球查看這個地標。';}};
    try{
      const {Map3DElement}=await mapsLibrary();
      if(id!==viewId)return;
      const map=new Map3DElement({center:{lat:place.lat,lng:place.lon,altitude:10},range:active===0?780:320,tilt:57,heading:32,mode:'SATELLITE'});
      map.addEventListener('gmp-error',failed,{once:true});host.replaceChildren(map);status.textContent='';
    }catch{failed();}
  };
  get('real-close').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>{viewId++;host.replaceChildren();});
})();
