"""Extract and reassemble roof outlines clipped at PMTiles boundaries."""
from collections import defaultdict
import gzip
import math
import zlib

import numpy as np
import shapely as geo
from mapbox_vector_tile import decode
from pmtiles.reader import MmapSource, Reader
from shapely.geometry import shape

def buildings_from_tiles(path, origin, factors, area):
    zoom=14
    count=2**zoom
    def tile(lon,lat):
        return int((lon+180)/360*count),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)*count/2)
    l,t,r,b=area.bounds
    x0,y0=tile(origin[0]+l/factors[0],origin[1]+t/factors[1])
    x1,y1=tile(origin[0]+r/factors[0],origin[1]+b/factors[1])
    fragments=defaultdict(list);attributes={}
    with open(path,'rb') as handle:
        reader=Reader(MmapSource(handle))
        for tx in range(x0,x1+1):
            for ty in range(y0,y1+1):
                packed=reader.get(zoom,tx,ty)
                if not packed:continue
                layer=decode(gzip.decompress(packed),default_options={'y_coord_down':True})['building']
                extent=layer['extent']
                def project(coords):
                    x=(tx+coords[:,0]/extent)/count
                    y=(ty+coords[:,1]/extent)/count
                    lon=x*360-180;lat=np.degrees(np.arctan(np.sinh(math.pi*(1-2*y))))
                    return np.stack([(lon-origin[0])*factors[0],(lat-origin[1])*factors[1]],axis=1)
                for f in layer['features']:
                    p=f['properties'];g=geo.transform(shape(f['geometry']),project)
                    if not area.intersects(g):continue
                    if not g.is_valid:g=geo.make_valid(g)
                    clipped=g.intersection(area)
                    if clipped.area<1:continue
                    fragments[p['id']].append(clipped);attributes[p['id']]=p
    result=[]
    for key,parts in fragments.items():
        p=attributes[key];outline=geo.union_all(parts).simplify(.32)
        for poly in geo.get_parts(outline):
            if poly.geom_type=='Polygon' and poly.area>=6:
                result.append((zlib.crc32(key.encode()),{'height':p['h'],'quality':p['q'],'nlsc':key},poly))
    return result
