"""Export the bridge primitives used by the district renderer for live plane intersections."""
import json
import math
import struct

from PIL import Image, ImageDraw

from architecture import Artist, bridge, kawabata


class BridgeSolids(Artist):
    def __init__(self):
        self.solids = []
        self.owner = 0

    def group(self, x, y, level=0):
        pass

    def record(self, points, face=False):
        # The city renderer also packs each coordinate in quarter metres.
        coords = [round(v * 4) for point in points for v in point]
        self.solids.append([self.owner, int(face), coords])

    def pier_web(self, front, back):
        self.record([*front,*back])

    def block(self, x, y, z, w, d, h, tone, heading=0, mat=0):
        c, s = math.cos(heading), math.sin(heading)
        base = [(x+u*c-v*s, y+u*s+v*c, z) for u,v in
                [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
        self.record(base + [(a,b,z+h) for a,b,_ in base])

    def stack(self, lower, upper, tone, cap=False):
        self.record([*lower, *upper])

    def quad(self, a, b, c, d, tone, *material):
        self.record([a,b,c,d], face=True)


def write_section(directory, start, end, old_axis, elevated, deck, bounds, pixel_size):
    solids = BridgeSolids()
    for g, w, tags in elevated:
        if tags.get('name') == '中正橋':
            deck(g,w+1.5,10,'9a9f92',solids.block,solids.group)
    bridge(solids,start,end,elevated)
    solids.owner = 1
    kawabata(solids,old_axis)

    north = math.ceil(end[1]+8)
    south = math.floor(start[1]-8)
    items = [s for s in solids.solids if min(s[2][1::3]) <= south*4 and max(s[2][1::3]) >= north*4]
    # A narrow geographic overview also shows both approaches.
    xs = [x/4 for _,_,coords in items for x in coords[::3]]
    left, right = math.floor(min(xs)-31), math.ceil(max(xs)+31)
    extent = [left,north-23,right,south+23]
    piers = sorted([old_axis.interpolate(j/10,normalized=True).y for j in range(1,10)])
    pier = min((y for y in piers if north+20<y<south-20),key=lambda y:abs(y-(north+south)/2))
    adjacent = piers[piers.index(pier)+1]
    cable = start[1]+(end[1]-start[1])*10/25
    meta = dict(extent=extent, north=north, south=south,
                presets=[round((south-y)*4)/4 for y in (pier,(pier+adjacent)/2,cable)],
                solids=items)
    (directory/'bridge-section.json').write_text(json.dumps(meta,separators=(',',':')))
    # Use the district's baked top view and draw the recorded bridge parts on top at finer resolution.
    scale = 4
    def xy(x,y):
        return (round((x-left)*scale),round((y-extent[1])*scale))
    base = Image.open(directory/'ground-streetscape.png').convert('RGB')
    crop = tuple((v-bounds[i%2])/pixel_size for i,v in enumerate(extent))
    plan = base.transform(((right-left)*scale,(extent[3]-extent[1])*scale),Image.Transform.EXTENT,crop,Image.Resampling.NEAREST)
    pen = ImageDraw.Draw(plan)
    for x,y,r,h,red,green,blue,_ in struct.iter_unpack('<4h4B',(directory/'trees.bin').read_bytes()):
        cx,cy=xy(x/4,y/4);radius=r/4*scale
        if -radius<cx<plan.width+radius and -radius<cy<plan.height+radius:
            pen.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),fill=(red,green,blue))
    polys=[]
    for owner,face,coords in solids.solids:
        points=list(zip(coords[::3],coords[1::3],coords[2::3]))
        n=len(points)//2
        faces=[points] if face else [points[n:]]+[[points[i],points[(i+1)%n],points[(i+1)%n+n],points[i+n]] for i in range(n)]
        for ring in faces:
            z=sum(p[2] for p in ring)/len(ring)/4
            tone=('#eee4c5' if z>13 else '#a0a9a0') if owner==0 else ('#e2c097' if z>=8.6 else '#86775e')
            polys.append((z,[xy(x/4,y/4) for x,y,_ in ring],tone))
    for _,ring,tone in sorted(polys,key=lambda item:item[0]):
        pen.polygon(ring,fill=tone)
    plan.save(directory/'bridge-plan.png',optimize=True)
