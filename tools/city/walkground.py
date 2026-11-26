"""Bake the illustrated river and the shared afternoon ground shadows."""
import gzip
import json
import random
import struct

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point
from shapely.prepared import prep


def river_ground(streets, dry, river, original_river, origin, resolution):
    """Preserve the original map for comparison and replace its buffered river in the illustrated view."""
    image=streets.copy()
    def pixel(x,y):
        return ((x-origin[0])/resolution,(y-origin[1])/resolution)
    def mask(geometry):
        result=Image.new('L',image.size);pen=ImageDraw.Draw(result)
        for polygon in getattr(geometry,'geoms',[geometry]):
            if polygon.geom_type!='Polygon' or polygon.is_empty:continue
            pen.polygon([pixel(x,y) for x,y in polygon.exterior.coords],fill=255)
            for hole in polygon.interiors:pen.polygon([pixel(x,y) for x,y in hole.coords],fill=0)
        return result
    before=np.asarray(image)[:,:,:3]
    was_water=np.zeros(before.shape[:2],dtype=bool)
    for c in ['79b3ad','8fc2b5','86bcb3','71aea9']:
        was_water|=(before==tuple(bytes.fromhex(c))).all(axis=2)
    image.paste(dry,mask=Image.fromarray(np.where(was_water,np.asarray(mask(original_river)),0).astype('uint8')))
    for inset,hexcolor in [(0,'b9c7a4'),(2.4,'93b8a7'),(6.3,'78aea5'),(13,'629e9e')]:
        patch=river.buffer(-inset) if inset else river
        image.paste('#'+hexcolor,(0,0,*image.size),mask(patch))
    rng=random.Random(312);water=prep(river.buffer(-13))
    pen=ImageDraw.Draw(image);l,t,r,b=river.bounds
    for _ in range(round((r-l)*(b-t)/126)):
        x=rng.uniform(l,r);y=rng.uniform(t,b)
        length=rng.uniform(2,9)
        if water.contains(Point(x,y)) and water.contains(Point(x+length,y)):
            pen.line([pixel(x,y),pixel(x+length,y+.25*length)],fill=rng.choice(['#7dafab','#6ca5a2','#83b4ad']))
    return image


def sunlight(directory, ground):
    data=json.loads((directory/'district.json').read_text())
    bounds=data['bounds'];resolution=data['groundPixelMeters']
    mask=Image.new('1',ground.size)
    pen=ImageDraw.Draw(mask)
    # East and south offsets per metre of height. Project each caster once into the same mask.
    sun=np.array([.52,.34],dtype=np.float32)
    dtype=np.dtype([('xyz','<i2',(3,)),('rest','u1',(6,))])
    for name in ('streetscape','shared'):
        with gzip.open(directory/(name+'.mesh.gz'),'rb') as f:
            while raw:=f.read(36*32000):
                xyz=np.frombuffer(raw,dtype=dtype)['xyz'].reshape(-1,3,3).astype(np.float32)*.25
                xyz=xyz[xyz[:,:,2].max(axis=1)>.8]
                projected=(xyz[:,:,:2]+xyz[:,:,2,None]*sun-bounds[:2])/resolution
                ab,ac=projected[:,1]-projected[:,0],projected[:,2]-projected[:,0]
                area=abs(ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0])
                for pts in np.rint(projected[area>.28]).astype('int32').reshape(-1,6):
                    pen.polygon(pts.tolist(),fill=1)
    for x,y,r,h,red,green,blue,hide in struct.iter_unpack('<4h4B',(directory/'trees.bin').read_bytes()):
        if hide:continue
        cx,cy=(np.array([x,y])*.25+h*.17*sun-bounds[:2])/resolution
        radius=r*.25/resolution
        pen.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=1)
    tinted=ground.convert('RGB').point([round(i*k) for k in (.69,.76,.80) for i in range(256)])
    result=ground.copy();result.paste(tinted,mask=mask);result.putalpha(ground.getchannel('A'))
    result.save(directory/'ground-walk.png',optimize=True)
