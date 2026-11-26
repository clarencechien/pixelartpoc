"""Build a single metric map of Yonghe from the Taiwan OSM Parquet snapshot."""
import argparse
import gzip
import json
import math
import random
import struct
from collections import Counter, defaultdict
from nlsc import buildings_from_tiles
import architecture
import walkground
from pathlib import Path

import duckdb
import numpy as np
import shapely as geo
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import nearest_points, unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'dist/city'
OUT.mkdir(exist_ok=True)
origin = (121.515, 25.009)
sx, sy = 111320 * math.cos(math.radians(origin[1])), -110820
def xy(lon, lat):
    return ((lon-origin[0])*sx, (lat-origin[1])*sy)

def local(g):
    return affinity.affine_transform(g,[sx,0,0,sy,-sx*origin[0],-sy*origin[1]])

def pieces(g,kind):
    if g.geom_type==kind and not g.is_empty:
        yield g
    elif g.geom_type.startswith('Multi') or g.geom_type=='GeometryCollection':
        for part in g.geoms: yield from pieces(part,kind)

ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('elements',type=Path)
ap.add_argument('nlsc_tiles',type=Path)
args=ap.parse_args()
boundary=local(shape(json.loads((HERE/'yonghe-boundary.geojson').read_text())['geometry'])).simplify(1.5)
bridge_axis=LineString([xy(121.5158,25.01735),xy(121.5155,25.0203),xy(121.5158,25.02125),xy(121.51672,25.02245)])
area=unary_union([boundary.buffer(64),bridge_axis.buffer(105)]).simplify(1.5)
minx,miny,maxx,maxy=area.bounds
bounds=[math.floor(minx)-4,math.floor(miny)-4,math.ceil(maxx)+4,math.ceil(maxy)+4]
scale=1.25
width,height=(math.ceil((bounds[i+2]-bounds[i])/scale) for i in (0,1))
bounds[2]=bounds[0]+width*scale;bounds[3]=bounds[1]+height*scale
def raster(x,y):return ((x-bounds[0])/scale,(y-bounds[1])/scale)
def coords(g):return [raster(x,y) for x,y in g.coords]
def rgb(s):return tuple(bytes.fromhex(s))
def shade(c,f):return tuple(min(255,round(v*f)) for v in c)
def color(v):return rgb(v) if isinstance(v,str) else v
def number(value,default):
    try:return float(str(value).split(';')[0].removesuffix(' m'))
    except (TypeError,ValueError):return default

rows=duckdb.sql("""select id,typ,tags,geom_wkb from read_parquet(?)
 where x1>=121.49 and x0<=121.538 and y1>=24.99 and y0<=25.026 and typ in ('way','node')
 and (typ='way' or tags['highway']='crossing' or tags['natural']='tree' or tags['railway']='subway_entrance')
 order by id""",params=[str(args.elements/'part-*.parquet')]).fetchall()
ground=Image.new('RGBA',(width,height))
draw=ImageDraw.Draw(ground)
def paint(poly,c):
    draw.polygon(coords(poly.exterior),fill=color(c))
def line(p,c,w):
    draw.line([raster(x,y) for x,y in p],fill=color(c),width=max(1,round(w/scale)),joint='curve')
mapped_features={}
historic_bridge=[]
levees=[];river_bed=[]
roads=[]; buildings=[]; green=[]; water=[]; courts=[]; points=[]; markets=[]; other=[]
widths={'motorway':16,'trunk':14,'primary':15,'secondary':13,'tertiary':10,'residential':6,'service':4,'living_street':6,'unclassified':6,'cycleway':3,'pedestrian':4,'footway':2.1,'path':1.8,'steps':2}
for fid,typ,tags,wkb in rows:
    geom=local(geo.from_wkb(wkb))
    if not area.intersects(geom):continue
    if not geom.is_valid:geom=geo.make_valid(geom)
    geom=geom.intersection(area)
    if geom.geom_type=='Polygon' and (fid in (233926867,556975004,1245570809,556975017,1245570785,1245570801,1245570793,1245570781) or tags.get('natural')=='wood'):
        mapped_features[fid]=geom
    if tags.get('man_made')=='embankment' and geom.geom_type=='LineString':
        near_span=geom.intersection(Point(*xy(121.51566,25.01818)).buffer(420))
        levees.extend(pieces(near_span,'LineString'))
    if tags.get('name')=='川端橋' and tags.get('bridge')=='yes' and geom.geom_type=='LineString':
        historic_bridge.append(geom)
    h=tags.get('highway','').removesuffix('_link')
    if typ=='node':
        points.append((fid,tags,geom));continue
    if h in widths and tags.get('tunnel') not in ('yes','building_passage'):
        w=number(tags.get('width'),0)
        if not 1<=w<=42:
            lanes=number(tags.get('lanes'),0)
            w=max(widths[h]*.62,lanes*3.1+.8) if lanes else widths[h]
        for g in pieces(geom,'LineString'):
            if g.length>1:roads.append((fid,h,g,w,tags))
    if tags.get('waterway')=='river':
        for g in pieces(geom,'LineString'):
            band=list(pieces(g.buffer(72).intersection(area),'Polygon'));water.extend(band)
            if tags.get('name')=='新店溪':river_bed.extend(band)
    for g in pieces(geom,'Polygon'):
        if g.area<2:continue
        if 'building' in tags and tags['building'] not in ('no','construction','roof'):
            buildings.append((fid,tags,g.simplify(.32)))
        elif tags.get('natural')=='water':water.append(g)
        elif tags.get('leisure')=='pitch':courts.append((g,tags.get('sport','')))
        elif tags.get('landuse') in ('forest','grass','cemetery','recreation_ground','allotments','village_green') or tags.get('leisure') in ('park','garden','dog_park') or tags.get('natural') in ('wood','grassland'):green.append(g)
        elif tags.get('amenity')=='marketplace':markets.append(g)
        elif tags.get('landuse') in ('construction','religious','school') or tags.get('amenity') in ('school','university','college'):other.append(g)
for p in pieces(area,'Polygon'):paint(p,'c7c3aa')
for g in other:paint(g,'cbbda2')
for g in green:paint(g,'a4bc80')
for g in markets:paint(g,'d7b38d')
dry_ground=ground.copy()
for g in water:paint(g,'79b3ad')
for g,sport in courts:
    paint(g,'bd9177' if sport in ('baseball','basketball','tennis') else '88a585')
    line(g.exterior.coords,'dbd8ad',1.5)
    pts=list(g.minimum_rotated_rectangle.exterior.coords)
    if len(pts)==5 and sport in ('soccer','basketball','tennis'):
        a,b,c,d=pts[:4]
        line([((a[0]+b[0])/2,(a[1]+b[1])/2),((c[0]+d[0])/2,(c[1]+d[1])/2)],'dbd8ad',1.5)
rng=random.Random(735)
# Water ripples are clipped to the real river path, whose width is approximated.
for g in water:
    l,t,r,b=g.bounds
    for _ in range(int(g.area/72)):
        x,y=rng.uniform(l,r),rng.uniform(t,b)
        if g.contains(Point(x,y)):line([(x,y),(x+rng.uniform(2,8),y)],rng.choice(['8fc2b5','86bcb3','71aea9']),1.25)

# The first mesh pass is shared across quality levels, the second carries smaller objects.
chunks=defaultdict(bytearray)
vertex=struct.Struct('<hhh6B')
key=(0,0,0)
def group(x,y,detail=0):
    global key
    key=(detail,math.floor(x/256),math.floor(y/256))
def tri(a,b,c,tone,mat=0,direction=0,seed=0):
    attrs=(*color(tone),mat,direction,seed%256)
    buf=chunks[key]
    for x,y,z in (a,b,c):buf.extend(vertex.pack(round(x*4),round(y*4),round(z*4),*attrs))
def quad(a,b,c,d,*args):
    tri(a,b,c,*args);tri(a,c,d,*args)
def decal(points,uv):
    for i in (0,1,2,0,2,3):
        x,y,z=points[i];u,v=uv[i]
        chunks[key].extend(vertex.pack(round(x*4),round(y*4),round(z*4),255,255,255,6,u,v))
def block(x,y,z,w,d,h,tone,heading=0,mat=0):
    c,s=math.cos(heading),math.sin(heading);tone=color(tone)
    a=[(x+u*c-v*s,y+u*s+v*c,z) for u,v in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]
    b=[(u,v,z+h) for u,v,_ in a]
    for i in range(4):
        j=(i+1)%4;quad(a[i],a[j],b[j],b[i],shade(tone,[.89,.74,.82,.96][i]),mat)
    quad(*b,tone,mat)
def ring(x,y,z,rx,ry,offset=0):
    return [(x+rx*math.cos(i*math.pi/4+offset),y+ry*math.sin(i*math.pi/4+offset),z) for i in range(8)]
def stack(lo,hi,tone,cap=False):
    # Stitch horizontal sprite slices into an opaque shell for a single depth-tested district draw.
    tone=color(tone)
    for i in range(len(lo)):
        j=(i+1)%len(lo);quad(lo[i],lo[j],hi[j],hi[i],shade(tone,.82+.14*math.cos(i*math.pi/4+2.6)))
        if cap and i not in (0,len(lo)-1):tri(hi[0],hi[i],hi[j],tone)
def along(path,spacing,start):
    points=list(path.coords);rem=start
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        dx,dy=x1-x0,y1-y0;l=math.hypot(dx,dy)
        if not l:continue
        dx/=l;dy/=l
        while rem<l:
            yield x0+rem*dx,y0+rem*dy,dx,dy
            rem+=spacing
        rem-=l
def deck(path,w,z,tone,emit=block,locate=group):
    for (x,y),(a,b) in zip(path.coords,list(path.coords)[1:]):
        dx,dy=a-x,b-y
        if dx==dy==0:continue
        locate((x+a)/2,(y+b)/2);emit((x+a)/2,(y+b)/2,z-1.5,math.hypot(dx,dy)+.5,w,1.5,tone,math.atan2(dy,dx))

roadtree=STRtree([r[2] for r in roads])
elevated=[];drive=[];market_street=[]
for fid,h,g,w,tags in sorted(roads,key=lambda r:r[3]):
    walking=h in ('footway','steps','path','cycleway','pedestrian')
    if tags.get('bridge')=='yes' and not walking:
        elevated.append((g,w,tags));continue
    line(g.coords,'a4aa96' if walking else 'b1ac96',w+(1.3 if walking else 3))
    line(g.coords,('d4c8a4' if h!='cycleway' else 'b1b288') if walking else ('89918b' if w<8 else '7a8682'),w)
    if not walking:drive.append((g,w,tags))
    if tags.get('name')=='永平路':market_street.append(g)
for g,w,tags in drive:
    if w>8:
        for x,y,dx,dy in along(g,13,2):line([(x,y),(x+dx*4.5,y+dy*4.5)],'d5c58e',1.2)
for _,t,g in points:
    if t.get('highway')!='crossing' or t.get('crossing')=='unmarked':continue
    _,h,path,w,_=roads[int(roadtree.nearest(g))]
    if path.distance(g)>10:continue
    d=path.project(g);a=path.interpolate(max(0,d-2));b=path.interpolate(min(path.length,d+2))
    angle=math.atan2(b.y-a.y,b.x-a.x);dx,dy=math.cos(angle),math.sin(angle)
    for offset in np.arange(-w*.40,w*.41,1.65):
        x,y=g.x-dy*offset,g.y+dx*offset
        line([(x-1.8*dx,y-1.8*dy),(x+1.8*dx,y+1.8*dy)],'e2dfc8',.9)
# Reserve actual roads, parks and recorded footprints before filling missing street fronts.
reserve=Image.new('1',(width,height)); occ=ImageDraw.Draw(reserve)
for g in green+water+other+markets+[g for g,_ in courts]+[g for _,_,g in buildings]:
    occ.polygon(coords(g.exterior),fill=1)
for _,_,g,w,_ in roads:occ.line(coords(g),fill=1,width=max(2,round((w+2)/scale)))
bits=np.array(reserve);inferred=0
for g,w,t in drive:
    if w>20 or t.get('highway') not in ('residential','tertiary','secondary','living_street','unclassified'):continue
    for x,y,dx,dy in along(g,9,5):
        for side in (-1,1):
            front=rng.uniform(6.4,9);depth=rng.uniform(8,15);start=w/2+2.2
            pts=[(x+dx*u-dy*v*side,y+dy*u+dx*v*side) for u,v in [(-front/2,start),(front/2,start),(front/2,start+depth),(-front/2,start+depth)]]
            pix=[tuple(map(round,raster(*p))) for p in pts];xx,yy=zip(*pix);l,r=min(xx),max(xx);t0,b=min(yy),max(yy)
            if l<0 or t0<0 or r>=width or b>=height or bits[t0:b+1,l:r+1].all():continue
            mask=Image.new('1',(r-l+1,b-t0+1));ImageDraw.Draw(mask).polygon([(a-l,k-t0) for a,k in pix],fill=1);foot=np.array(mask)
            region=bits[t0:b+1,l:r+1]
            if np.any(region&foot) or not area.contains(Point(x,y)):continue
            region|=foot;inferred+=1
            buildings.append((-inferred,{},Polygon(pts)))
print('roads',len(roads),'buildings',len(buildings),'inferred',inferred,flush=True)

wall_colors=['d4b599','c5ae90','b79f88','b7b9a7','b6c4b6','ddb79d','c7b79f','c4c4b0','d6c7ac','c9a28c']
roof_colors=['d7d1ba','cec8b3','e0d7c1','c1c5af','b9c2b6','cbbd9e']
def bake_buildings(rows,level):
    global ground,draw
    shadow=Image.new('1',(width,height)); shadowpen=ImageDraw.Draw(shadow)
    for fid,t,g in rows:
        if g.area<6:continue
        randomizer=random.Random(fid & 0xffffffff)
        x,y=g.centroid.coords[0];group(x,y,level)
        floors=number(t.get('building:levels'),randomizer.choice([2,3,3,4,4,5,6,7]))
        h=max(2,min(175,number(t.get('height'),1.3 if t.get('building')=='shed' else floors*3.15)))
        base=max(0,min(h-1,number(t.get('min_height'),0)))
        walls=rgb(randomizer.choice(wall_colors));roof=rgb(randomizer.choice(roof_colors))
        if len(g.exterior.coords)>110:g=g.simplify(.6)
        if not g.is_valid:continue
        for triangle in geo.get_parts(geo.constrained_delaunay_triangles(g)):
            tri(*[(u,v,h) for u,v in list(triangle.exterior.coords)[:3]],roof,2,0,fid)
        for ring_ in [g.exterior,*g.interiors]:
            for (u,v),(a,b) in zip(ring_.coords,list(ring_.coords)[1:]):
                angle=math.atan2(b-v,a-u)
                light=.81+.15*math.cos(angle+.7)
                quad((u,v,base),(a,b,base),(a,b,h),(u,v,h),shade(walls,light),1,round((angle%(2*math.pi))*255/(2*math.pi)),fid)
        if h<1:continue
        shifted=[raster(u+h*.49,v+h*.30) for u,v in g.exterior.coords]
        shadowpen.polygon(shifted,fill=1)
        # Roof and footprint are also legible in the software fallback and district overview.
        paint(g,shade(roof,.94))
        if level==2 or g.area<45:continue
        group(x,y,4)
        q=g.representative_point();px,py=q.x,q.y
        clearance=g.boundary.distance(q)
        if clearance>2.2:
            r=min(5.4,clearance*.48); a=randomizer.choice([0,.18,-.25,.48])
            metal=randomizer.choice(['6e9991','a87b65','af9c82','91a6a0','839d97'])
            block(px,py,h,2*r,1.45*r,randomizer.uniform(1.2,2.7),metal,a,3)
            if clearance>3.6:
                tx,ty=px+r*1.2,py-r*.75
                stack(ring(tx,ty,h,1.05,1.05),ring(tx,ty,h+2.1,1.05,1.05),'9ea8a2',True)
    shadowed=Image.fromarray((np.asarray(ground)[:,:,:3]*[.84,.88,.87]).astype('uint8')).convert('RGBA')
    shadowed.putalpha(ground.getchannel('A'));ground.paste(shadowed,mask=shadow)
    draw=ImageDraw.Draw(ground)

channel=local(shape(json.loads((HERE/'xindian-water.geojson').read_text())['geometry'])).intersection(area)
walk_ground=walkground.river_ground(ground,dry_ground,channel,unary_union(river_bed),bounds,scale)
base_ground=ground.copy()
bake_buildings(buildings,2)
low_ground=ground
ground=base_ground
draw=ImageDraw.Draw(ground)
official=buildings_from_tiles(args.nlsc_tiles,origin,(sx,sy),area)
if not official:raise ValueError('Empty NLSC district extract')
roof_tree=STRtree([g for _,_,g in official])
def missing_in_tiles(row):
    fid,tags,g=row
    if fid<0:return False
    candidates=roof_tree.query(g,predicate='intersects')
    if not len(candidates):return True
    occluded=unary_union([official[i][2] for i in candidates]).intersection(g).area
    return occluded<g.area*.08
supplement=[row for row in buildings if missing_in_tiles(row)]
bake_buildings(official+supplement,3)
print('NLSC polygons',len(official),'OSM supplement',len(supplement),flush=True)
for g,w,tags in elevated:
    z=10 if tags.get('name')=='中正橋' else 7
    deck(g,w+1.5,z,'9a9f92')
    for x,y,dx,dy in along(g,46,14):
        between_abutments=xy(0,25.021)[1]<y<xy(0,25.01922)[1]
        group(x,y,7 if tags.get('name')=='中正橋' and between_abutments else 0)
        block(x,y,0,max(2.4,w*.22),2.8,z-1,'adb19b')
    for x,y,dx,dy in along(g,12,3):
        group(x,y,1);block(x,y,z,4,.65,.32,'ead6a2',math.atan2(dy,dx))

# Bridge span over the river, anchored to geographic coordinates on both approaches.
p0=xy(121.51557,25.01922);p1=xy(121.51564,25.02100)
vx,vy=p1[0]-p0[0],p1[1]-p0[1];length=math.hypot(vx,vy);nx,ny=-vy/length,vx/length
def bridge_pos(t,side):return p0[0]+vx*t+nx*side,p0[1]+vy*t+ny*side
for side in [-10.7,10.7]:
    previous=None
    for j in range(81):
        t=j/80; x,y=bridge_pos(t,side);z=10+43*math.sin(math.pi*t)**.83
        group(x,y,7)
        if previous:
            a,b,h=previous;lo=ring(a,b,h,1.85,1.85);hi=ring(x,y,z,1.85,1.85);stack(lo,hi,'eee9cc',True)
        if j%9==3 and side>0:
            a,b=bridge_pos(t,-10.7)
            group(x,y,8);block((x+a)/2,(y+b)/2,z,math.hypot(x-a,y-b),.9,.9,'d4d6c0',math.atan2(y-b,x-a))
            group(x,y,7)
        if j%7==0 and z>11:block(x,y,10,.77,.77,z-10,'d6d9c5')
        previous=x,y,z

# Mapped trees plus groups inside recorded parks, using horizontal canopy slices.
park_union=unary_union(green) if green else Polygon()
trees=[(pos.x,pos.y) for _,t,pos in points if t.get('natural')=='tree']
for g in pieces(park_union,'Polygon'):
    l,t,r,b=g.bounds
    for _ in range(round((r-l)*(b-t)/94)):
        x,y=rng.uniform(l,r),rng.uniform(t,b)
        if g.contains(Point(x,y)) and not any(c.contains(Point(x,y)) for c,_ in courts if c.bounds[0]<=x<=c.bounds[2]):trees.append((x,y))
# Store each tree as a single instance, reusing the same stack of canopy slices.
renai=mapped_features[233926867]
woods=unary_union([g for fid,g in mapped_features.items() if fid!=233926867 and renai.contains(g.centroid) and fid not in (556975004,1245570809,556975017,1245570785,1245570801,1245570793,1245570781)])
open_park=renai.difference(woods).union(unary_union([mapped_features[k] for k in (556975004,1245570809,556975017,1245570785)]).buffer(2))
# Leave clearance for canopies along the edges of both bridge decks.
bridge_clearance = unary_union([g.buffer(w/2 + 5.8) for g, w, _ in elevated]
                               + [g.buffer(8.2) for g in historic_bridge])
clear_ground = unary_union([open_park, channel, bridge_clearance])
geo.prepare(clear_ground)
tree_cells=defaultdict(bytearray)
for x,y in trees:
    radius=rng.uniform(2.9,5.1);trunk=rng.uniform(2,3.8)
    tone=rgb(rng.choice(['739766','7c9c5c','819f65','68936d','92a766']))
    tree_cells[(math.floor(x/256),math.floor(y/256))].extend(struct.pack(
        '<4h4B',round(x*4),round(y*4),round(radius*4),round((trunk+radius*2)*4),*tone,255 if clear_ground.covers(Point(x,y)) else 0))
tree_spans=[];tree_count=0
with (OUT/'trees.bin').open('wb') as f:
    for (tx,ty),buf in sorted(tree_cells.items()):
        n=len(buf)//12;tree_spans.append([tx,ty,tree_count,n]);f.write(buf);tree_count+=n
# Parked and moving-lane vehicles are fixed illustrations at street scale.
for g,w,t in drive:
    if w<7 or g.length<25 or t.get('name')=='永平路':continue
    for x,y,dx,dy in along(g,rng.uniform(40,62),rng.uniform(10,28)):
        side=rng.choice([-1,1]);px=x-dy*side*w*.24;py=y+dx*side*w*.24
        a=math.atan2(dy,dx);group(px,py,1)
        tone=rng.choice(['c16d55','d6b86d','b9c9bd','789b9c','cfcec1'])
        block(px,py,.08,4.5,1.9,.83,tone,a)
        block(px-.15*dx,py-.15*dy,.91,2.55,1.59,.65,'6e8587',a)
        block(px-.17*dx,py-.17*dy,1.57,1.55,1.51,.17,tone,a)

station=xy(121.515482,25.014196);x,y=station;group(x,y,7)
block(x,y,0,13,6.4,3.5,'7f9e96');block(x,y,3.5,15.2,7.5,1.2,'72a395')
group(x,y,8)
for j in range(-3,4):block(x+j*1.8,y,4.7,.34,7.5,.25,'c6d6bc')
block(x+7.6,y,0,.75,.75,5.8,'7c8375');block(x+7.6,y,5.5,2.4,1.1,1.9,'e6b65e')
# Market stalls sit alongside Yongping Road, clipped to the mapped market.
market=unary_union(markets).buffer(6) if markets else Polygon()
for g in market_street:
    for x,y,dx,dy in along(g,6.3,2):
        if not market.contains(Point(x,y)):continue
        for side in [-1,1]:
            px,py=x-dy*side*3.8,y+dx*side*3.8;a=math.atan2(dy,dx)
            group(px,py,7);block(px,py,0,4,2,1.1,'a78c63',a)
            tone=rgb(rng.choice(['bb6c51','d8ab64','739d93','c77d5d']))
            block(px,py,2.3,4.8,3.3,.72,tone,a)
            group(px,py,8)
            for j in [-1.5,0,1.5]:block(px+dx*j,py+dy*j,3,.56,3.2,.2,'e8cba0',a)
            for j in [-1.6,1.6]:block(px+dx*j,py+dy*j,1,.19,.26,1.4,'766b53',a)

# The thin exposed edge gives the irregular district silhouette a base.
for poly in pieces(area.simplify(3),'Polygon'):
    for (x,y),(u,v) in zip(poly.exterior.coords,list(poly.exterior.coords)[1:]):
        group((x+u)/2,(y+v)/2);quad((x,y,-20),(u,v,-20),(u,v,0),(x,y,0),'a39b7c')
# Reapply a single continuous outline after drawing near edges.
alpha=Image.new('L',ground.size);brush=ImageDraw.Draw(alpha)
for g in pieces(area,'Polygon'):brush.polygon(coords(g.exterior),fill=255)
ground.putalpha(alpha)
ground.save(OUT/'ground-fine.png',optimize=True)
low_ground.putalpha(alpha)
low_ground.resize((width//2,height//2),Image.Resampling.NEAREST).save(OUT/'ground-low.png',optimize=True)
# Keep the previous high-detail envelope intact for the comparison mode.
art=architecture.Artist(tri,quad,block,stack,group,decal,OUT)
temple_site=next(g for _,tags,g in buildings if tags.get('name')=='永和保福宮')
temple_center=temple_site.centroid
entry=Point(*station)
stage_site=mapped_features[556975004]
street_graph=STRtree([g for g,w,t in drive])
guide_roads=[g for g,w,t in drive if t.get('name') in ('永和路二段','永和路一段','永平路') and g.intersects(geo.box(*xy(121.5098,25.0176),*xy(121.5168,25.0083)))]
guide_tree=STRtree(guide_roads)
landmark_points=[temple_center,entry,Point(*xy(121.51372,25.00872)),Point(*xy(121.51555,25.02012))]
for fid,tags,g in official+supplement:
    if temple_site.intersects(g) and temple_site.intersection(g).area>g.area*.42:continue
    precise_height=number(tags.get('height'),number(tags.get('building:levels'),4)*3.15)
    ctr=g.centroid
    near=any(ctr.distance(point)<195 for point in landmark_points)
    road=drive[int(street_graph.nearest(ctr))][0]
    if g.covers(entry) and tags.get('nlsc'):
        architecture.station(art,station,g,precise_height)
        continue
    if g.intersection(stage_site).area>g.area*.45:continue
    frontage=guide_roads[int(guide_tree.nearest(ctr))]
    on_walk=frontage.distance(g)<13 and xy(0,25.01755)[1]<ctr.y<xy(0,25.00812)[1]
    architecture.apartment(art,fid,tags,g,max(2,min(175,precise_height)),frontage if on_walk else road,near or on_walk,on_walk)
for levee in levees:
    for (x,y),(u,v) in zip(levee.coords,list(levee.coords)[1:]):
        length=math.hypot(u-x,v-y)
        if length<.1:continue
        dx,dy=(u-x)/length,(v-y)/length
        # Face the grass slope toward the river north of the riverside road.
        nx,ny=(-dy,dx) if dx<0 else (dy,-dx)
        group(x,y,5)
        quad((x,y,2.5),(u,v,2.5),(u+nx*6,v+ny*6,.15),(x+nx*6,y+ny*6,.15),'91a77d')
        block((x+u)/2,(y+v)/2,.1,length+.2,.95,2.42,'a9aa91',math.atan2(dy,dx))
        block((x+u)/2,(y+v)/2,2.5,length+.22,1.45,.25,'dad2af',math.atan2(dy,dx))
architecture.temple(art,architecture.Frame(temple_center.x,temple_center.y))
architecture.renai(art,mapped_features)
old_axis=geo.line_merge(geo.union_all(historic_bridge))
architecture.kawabata(art,old_axis)
architecture.market(art,market_street,market,xy(121.51399,25.00867))
architecture.bridge(art,p0,p1,elevated)
art.save_signs()
meshes={}
for name,levels in [('shared',(0,1)),('baseline-props',(7,8)),('low',(2,)),('fine',(3,4)),('streetscape',(5,6))]:
    spans=[];offset=0
    with gzip.GzipFile(str(OUT/(name+'.mesh.gz')),'wb',compresslevel=8,mtime=0) as f:
        for (detail,tx,ty),buf in sorted(chunks.items()):
            if detail not in levels:continue
            count=len(buf)//vertex.size;spans.append([int(detail in (1,4,6,8)),tx,ty,offset,count]);f.write(buf);offset+=count
    meshes[name]=spans
metadata={'origin':origin,'metersPerDegree':[sx,sy],'bounds':bounds,'groundPixelMeters':scale,'meshes':meshes,'nlscFootprints':len(official),'nlscHeights':dict(Counter(t['quality'] for _,t,_ in official)),'osmSupplement':len(supplement),'stride':vertex.size,'treeCells':tree_spans,
    'recordedBuildings':len(buildings)-inferred,'inferredBuildings':inferred,'roadSegments':len(roads),'crossingNodes':sum(t.get('highway')=='crossing' for _,t,_ in points)}
# Trace a street-aligned reading line through shared road vertices; it is illustrative.
from heapq import heappop, heappush
graph=defaultdict(list)
for _,h,g,w,tags in roads:
    if h in ('motorway','trunk') or tags.get('access')=='private':continue
    nodes=[(round(x,1),round(y,1)) for x,y in g.coords]
    for a,b in zip(nodes,nodes[1:]):
        cost=math.dist(a,b)*(1.03 if h in ('service','steps') else 1)
        graph[a].append((b,cost));graph[b].append((a,cost))
def street_path(start,end):
    start=min(graph,key=lambda p:math.dist(p,start));end=min(graph,key=lambda p:math.dist(p,end))
    queue=[(0,start)];dist={start:0};parents={}
    while queue:
        total,node=heappop(queue)
        if node==end:break
        if total!=dist[node]:continue
        for neighbor,cost in graph[node]:
            candidate=total+cost
            if candidate<dist.get(neighbor,math.inf):
                dist[neighbor]=candidate;parents[neighbor]=node;heappush(queue,(candidate,neighbor))
    if end not in parents:raise ValueError('Disconnected landmark street path')
    route=[end]
    while route[-1]!=start:route.append(parents[route[-1]])
    return list(LineString(route[::-1]).simplify(.9).coords)
stops=[xy(121.51555,25.02012),xy(121.515482,25.014196),xy(121.51372,25.00872)]
metadata['route']=[street_path(a,b) for a,b in zip(stops,stops[1:])]
metadata['outline']=[list(p.exterior.simplify(12).coords) for p in pieces(area,'Polygon')]

(OUT/'district.json').write_text(json.dumps(metadata,separators=(',',':')))
print('map dimensions',width,height,'vertices',offset,'files',[(p.name,p.stat().st_size) for p in OUT.glob('*')],flush=True)
walk_ground.putalpha(alpha)
walkground.sunlight(OUT,walk_ground)
from roofmap import bake as bake_roof_map
bake_roof_map(OUT)

from sections import write_section
write_section(OUT,p0,p1,old_axis,elevated,deck,bounds,scale)
