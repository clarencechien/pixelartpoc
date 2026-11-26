"""Bake a legible top view of the illustrated scene for devices without WebGL."""
import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw

def bake(directory):
    data=json.loads((directory/'district.json').read_text())
    ground=Image.open(directory/'ground-walk.png').convert('RGBA')
    brush=ImageDraw.Draw(ground)
    faces=[]
    dtype=np.dtype([('p','<i2',(3,)),('c','u1',(3,)),('material','u1',(3,))])
    for name in ('streetscape','shared'):
        with gzip.open(directory/(name+'.mesh.gz'),'rb') as f:vertices=np.frombuffer(f.read(),dtype=dtype).reshape(-1,3)
        pos=vertices['p'].astype(np.float32)*.25
        ab=pos[:,1,:2]-pos[:,0,:2];ac=pos[:,2,:2]-pos[:,0,:2]
        keep=np.abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0])>.35
        faces.append((pos[keep],vertices['c'][keep,0]))
    pos=np.concatenate([p for p,c in faces]);colors=np.concatenate([c for p,c in faces])
    xy=np.rint((pos[:,:,:2]-data['bounds'][:2])/data['groundPixelMeters']).astype(np.int32).reshape(-1,6)
    for i in np.argsort(pos[:,:,2].mean(axis=1),kind='stable'):
        brush.polygon(xy[i].tolist(),fill=tuple(colors[i].tolist()))
    ground.save(directory/'ground-streetscape.png',optimize=True)

if __name__=='__main__':bake(Path(__file__).resolve().parents[2]/'dist/city')
