"""Rebuild the river outline from the pinned Sentinel index tiles covering Yonghe."""
from functools import lru_cache
from io import BytesIO
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import shapely as geo
from PIL import Image, ImageFilter
from pmtiles.reader import Reader
from shapely.geometry import Point, box, mapping

REVISION = '3ebd023f9d21c45aa13eef0afaec53ce94219169'
SOURCE = ('https://huggingface.co/datasets/yhzkiki/taiwan-nlsc-imagery/resolve/'
          + REVISION + '/sentinel/ndvi-ndwi-2025.pmtiles')
FIRST_X, FIRST_Y = 13720, 7014
WORLD_PIXELS = 256 * 2**14


@lru_cache(None)
def read_range(offset, length):
    request = Request(f'{SOURCE}?offset={offset}&length={length}',
                      headers={'Range':f'bytes={offset}-{offset+length-1}'})
    with urlopen(request, timeout=45) as response:
        if response.status != 206:
            raise OSError('The PMTiles server did not return a byte range')
        return response.read(length)


def to_lonlat(coords):
    x = (coords[:,0] + FIRST_X*256) / WORLD_PIXELS
    y = (coords[:,1] + FIRST_Y*256) / WORLD_PIXELS
    return np.column_stack((x*360-180,np.degrees(np.arctan(np.sinh(np.pi*(1-2*y))))))


def main():
    reader = Reader(read_range)
    mosaic = Image.new('RGB',(1024,1024))
    for i in range(4):
        for j in range(4):
            tile = Image.open(BytesIO(reader.get(14,FIRST_X+i,FIRST_Y+j)))
            mosaic.paste(tile,(i*256,j*256))
    values = np.asarray(mosaic)
    wet = (values[:,:,1]>=143) & (values[:,:,0]<=138) & (values[:,:,2]>0)
    mask = Image.fromarray(wet.astype('uint8')*255)
    mask = mask.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MinFilter(9)).filter(ImageFilter.MedianFilter(3))
    runs = []
    for y,row in enumerate(np.asarray(mask)):
        bounds = np.flatnonzero(np.diff(np.r_[False,row>0,False]))
        runs.extend(box(left,y,right,y+1) for left,right in zip(bounds[::2],bounds[1::2]))
    lon,lat=121.514,25.021
    seed=Point((lon+180)/360*WORLD_PIXELS-FIRST_X*256,
               (1-math.asinh(math.tan(math.radians(lat)))/math.pi)*WORLD_PIXELS/2-FIRST_Y*256)
    channel=next(g for g in geo.get_parts(geo.union_all(runs)) if g.covers(seed))
    outline=geo.transform(channel.buffer(1.7).buffer(-1.7).simplify(.65),to_lonlat)
    outline=geo.set_precision(outline.intersection(box(121.488,24.989,121.542,25.0265)),.000001)
    feature={'type':'Feature','properties':{'source':'Contains modified Copernicus Sentinel data','layer':'S2IDX2025',
             'threshold':'G >= 143, R <= 138, B > 0; 9-pixel closing, 3-pixel median, connected Xindian channel'},
             'geometry':mapping(outline)}
    Path(__file__).with_name('xindian-water.geojson').write_text(json.dumps(feature,separators=(',',':'))+'\n')


if __name__=='__main__':
    main()
