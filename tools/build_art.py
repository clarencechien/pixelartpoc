"""Bake OSM footprints and original pixel models into bottom-to-top PNG slice atlases."""
import json
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'dist/assets'
ASSETS.mkdir(exist_ok=True)
def ink(color):
    return int(color.lstrip('#'), 16)

def tint(color, factor):
    return sum(min(255, int(((color >> shift) & 255) * factor)) << shift for shift in (16, 8, 0))

def rgba(array):
    return Image.fromarray(np.stack([(array >> 16) & 255, (array >> 8) & 255, array & 255, (array != 0)*255],axis=-1).astype('uint8'))

PALETTES = [
    ('cba78a','f0d5ab','a56957'), ('c6bf9f','e3e1c7','65908b'), ('c79b83','e8b79a','9e695b'),
    ('a4b5ab','d3d5ba','548281'), ('c3a68b','e3c5a3','b07d60'), ('b8a88c','dcceb1','688c83'),
    ('a1b2a7','c8d0b9','739697'), ('ceb493','eed3aa','976b55')]
def build(slug):
    data=json.loads((ROOT/'tools/geodata'/f'{slug}.json').read_text())
    n=data['size']; unit=data['unit']; features=data['features']
    rng=random.Random(171+ord(slug[0])); noise=np.random.default_rng(81)
    args=lambda p:[tuple(map(round,v)) for v in p]
    ground=Image.new('I',(n,n),ink('c3bc9c'))
    dr=ImageDraw.Draw(ground)
    mask=Image.new('L',(n,n)); pen=ImageDraw.Draw(mask)
    reserve=Image.new('L',(n,n)); border=ImageDraw.Draw(reserve)
    structures=[]; routes=[]; raised=[]; stalls=[]; court=[]
    def area(p, color, kind=None):
        dr.polygon(p,fill=ink(color))
        if kind is not None: pen.polygon(p,fill=kind)
    for i,t,typ,pts in sorted(features,key=lambda f: f[1].get('natural')=='water'):
        if typ!='Polygon':continue
        p=args(pts)
        if t.get('leisure') in ('park','garden','dog_park','fitness_station') or t.get('landuse') in ('grass','forest','village_green','recreation_ground','flowerbed'):
            area(p,rng.choice(['99b876','a4bd7c','aac383','a4bd78']),1)
        if t.get('leisure')=='pitch':court.append((p,t.get('sport')))
        if t.get('natural')=='water':
            area(p,'6faea5',2)
            dr.line(p,fill=ink('88c6b3'),width=5)
    for p,sport in court:
        area(p,'779e85' if sport=='soccer' else 'bc906f',3)
        dr.line(p,fill=ink('e5d9ad'),width=1)
    # Quiet variations and small, connected clusters give water and grass scale.
    groundarr=np.array(ground); zones=np.array(mask)
    dr=ImageDraw.Draw(ground)
    for _ in range(n*n//7):
        x=rng.randrange(n);y=rng.randrange(n);z=zones[y,x]
        if z==2:
            if rng.random()<.32:dr.line((x,y,x+rng.randrange(2,10),y),fill=ink(rng.choice(['88c2b4','80b9ae','9bccbb','69a79f'])))
        elif rng.random()<.38:
            dr.line((x,y,x+rng.randrange(1,4),y),fill=tint(int(groundarr[y,x]),rng.choice([.96,1.04])))
    widths={'motorway':15,'trunk':12,'primary':15,'secondary':12,'tertiary':10,'residential':6.5,'living_street':6,'service':4,'footway':2,'cycleway':3,'path':2,'pedestrian':4,'steps':2,'unclassified':6}
    for i,t,typ,pts in features:
        if typ=='Polygon' and t.get('building') and t['building'] not in ('roof','construction'):
            p=args(pts); structures.append((i,t,p))
            border.polygon(p,fill=255)
        h=t.get('highway','').split('_link')[0]
        if typ!='LineString' or h not in widths or t.get('tunnel') in ('yes','building_passage'):continue
        p=args(pts); w=max(2,round(widths[h]/unit))
        border.line(p,fill=255,width=w+4)
        if t.get('bridge')=='yes' and h not in ('path','footway','cycleway'):
            raised.append((p,w,t));continue
        routes.append((w,p,h,t))
    routes.sort(key=lambda r:r[0])
    for w,p,h,t in routes:
        path=h in ('footway','cycleway','steps','path','pedestrian')
        dr.line(p,fill=ink('9ba38b' if path else 'a19d88'),width=w+4)
        dr.line(p,fill=ink('cfca9d' if path else '7f8881'),width=w)
    def along(p,gap,start=0):
        distance=start
        for (x0,y0),(x1,y1) in zip(p,p[1:]):
            length=math.hypot(x1-x0,y1-y0)
            if not length:continue
            dx,dy=(x1-x0)/length,(y1-y0)/length
            while distance<length:
                yield x0+dx*distance,y0+dy*distance,dx,dy
                distance+=gap
            distance-=length
    cars=[]
    for w,p,h,t in routes:
        if h in ('residential','primary','secondary','tertiary','trunk','living_street'):
            if w>=7:
                for x,y,dx,dy in along(p,11,3):
                    dr.line((x,y,x+3.6*dx,y+3.6*dy),fill=ink('dfcc88'),width=1)
            for x,y,dx,dy in along(p,rng.randrange(35,58),rng.randrange(10,31)):
                side=rng.choice([-1,1]);cars.append((round(x-dy*w*.24*side),round(y+dx*w*.24*side),dx,dy,0))
    vol=np.zeros((118,n,n),dtype=np.uint32)
    def disc(z,x,y,r,c):
        if z<1 or z>=len(vol) or not (0<=x<n and 0<=y<n):return
        x=int(x);y=int(y);r=max(0,int(r))
        x0=max(0,x-r);x1=min(n,x+r+1);y0=max(0,y-r);y1=min(n,y+r+1)
        yy,xx=np.ogrid[y0:y1,x0:x1]
        vol[z,y0:y1,x0:x1][(xx-x)**2+(yy-y)**2<=r*r+1]=c
    def cuboid(x0,y0,z0,x1,y1,z1,color):
        vol[max(1,z0):min(len(vol),z1+1),max(0,y0):max(0,min(n,y1+1)),max(0,x0):max(0,min(n,x1+1))]=color
    # Fill unmapped street fronts with illustrative massing only inside unused urban lots.
    street_mask=np.array(reserve)>0
    if slug=='lehua':
        for w,p,h,t in routes:
            if t.get('name')!='永平路':continue
            for x,y,dx,dy in along(p,10,5):
                for side in [-1,1]:
                    cx=round(x-dy*side*(w/2+1));cy=round(y+dx*side*(w/2+1))
                    if 4<cx<n-5 and 4<cy<n-5:stalls.append((cx,cy))
    # Extend street fronts where the snapshot has road geometry but no building outline.
    # Align every inferred footprint with its road and reserve mapped open space.
    occupied=np.array(reserve)>0
    occupied |= zones>0
    for i,t,typ,pts in features:
        if typ=='Polygon' and (t.get('leisure') or t.get('landuse') in ('construction','grass','forest','flowerbed','allotments')):
            im=Image.new('1',(n,n));ImageDraw.Draw(im).polygon(args(pts),fill=1);occupied |= np.array(im)
    synthetic=0
    for w,p,h,t in sorted(routes, key=lambda item:-item[0]):
        if h not in ('secondary','tertiary','residential','living_street','service','unclassified'):continue
        if t.get('name','').startswith('中正橋'):continue
        for x,y,dx,dy in along(p,max(5,round(7/unit)),rng.randrange(1,6)):
            for side in (-1,1):
                frontage=rng.uniform(5.2,10)/unit; depth=rng.uniform(8,17)/unit
                start=w/2+2.7
                def corner(along_road,away):
                    return (round(x+dx*along_road-side*dy*away),round(y+dy*along_road+side*dx*away))
                outline=[corner(-frontage/2,start),corner(frontage/2,start),corner(frontage/2,start+depth),corner(-frontage/2,start+depth)]
                xs,ys=zip(*outline); x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys)
                if x0<0 or y0<0 or x1>=n or y1>=n:continue
                im=Image.new('1',(x1-x0+1,y1-y0+1));ImageDraw.Draw(im).polygon([(a-x0,b-y0) for a,b in outline],fill=1)
                footprint=np.array(im);part=occupied[y0:y1+1,x0:x1+1]
                if np.any(part & footprint):continue
                part |= footprint;synthetic+=1
                structures.append((-synthetic,{'building:levels':str(rng.choice([2,3,3,4,4,5,6]))},outline+[outline[0]]))
    treepoints=[]
    for _ in range(n*7):
        x=rng.randrange(3,n-3);y=rng.randrange(3,n-3)
        if street_mask[y,x] or zones[y,x]!=1:continue
        if rng.random()<.72 and (math.sin(x*.05)+math.cos(y*.043)<.2):continue
        treepoints.append((x,y,rng.choice([3,3,4,5])))
    for i,t,typ,p in features:
        if t.get('natural')=='tree' and typ=='Point':treepoints.append((*args(p)[0],rng.choice([3,4,5])))
    # Sun from northwest: cast ground shadows before compositing the slice strips.
    groundbase=ground.convert('I'); shade=Image.new('L',(n,n)); sh=ImageDraw.Draw(shade)
    specs=[]
    for i,t,p in structures:
        try: floors=float(t.get('building:levels',0))
        except ValueError:floors=0
        if not floors:
            try:floors=float(t.get('height','0').split()[0])/3
            except (ValueError,IndexError):floors=0
        if not floors:floors=rng.choice([2,3,3,4,4,5,6,6,7])
        if t.get('building') in ('garage','shed','kiosk'):floors=1
        # Compress tall towers slightly so adjacent streets remain visible.
        ht=max(3,min(98,round((min(floors,8)+max(0,floors-8)*.67)*3.1/unit)))
        specs.append((i,p,ht))
        sh.polygon([(x+round(ht*.53),y+round(ht*.32)) for x,y in p],fill=1)
        for a,b in zip(p,p[1:]):
            sh.polygon([a,b,(b[0]+round(ht*.53),b[1]+round(ht*.32)),(a[0]+round(ht*.53),a[1]+round(ht*.32))],fill=1)
    for x,y,r in treepoints:sh.ellipse((x,y,x+r*3,y+r*2),fill=1)
    plane=np.asarray(groundbase).astype('uint32')
    shadow=np.array(shade)>0
    shadowcolor=((plane>>16)*.81).astype('uint32')<<16 | (((plane>>8)&255)*.84).astype('uint32')<<8 | ((plane&255)*.83).astype('uint32')
    vol[0]=np.where(shadow,shadowcolor,plane)
    # Bake repeated horizontal slices with walls, balcony bands, glazing and roof furniture.
    for fid,p,ht in specs:
        x0=max(0,min(x for x,y in p));x1=min(n-1,max(x for x,y in p))
        y0=max(0,min(y for x,y in p));y1=min(n-1,max(y for x,y in p))
        if x1-x0<2 or y1-y0<2:continue
        im=Image.new('L',(x1-x0+1,y1-y0+1));ImageDraw.Draw(im).polygon([(x-x0,y-y0) for x,y in p],fill=255)
        inside=np.array(im)>0
        pad=np.pad(inside,1); left=~pad[1:-1,:-2]&inside; north=~pad[:-2,1:-1]&inside
        east=~pad[1:-1,2:]&inside;south=~pad[2:,1:-1]&inside
        interior=np.array(im.filter(ImageFilter.MinFilter(3)))>0
        rim=(left|north|east|south)
        body,light,accent=map(ink,rng.choice(PALETTES))
        mat=np.where(east|south,tint(body,.76),body).astype('uint32')
        mat[north]=tint(body,1.06);mat[left]=tint(body,.91)
        yy,xx=np.indices(inside.shape);phase=rng.randrange(7)
        stride=max(3,round(3.7/unit));step=max(3,round(3.2/unit))
        windows=(((xx+x0+phase)%stride<max(1,stride//2))&(north|south))|(((yy+y0)%stride<max(1,stride//2))&(east|left))
        views=vol[:,y0:y1+1,x0:x1+1]
        for z in range(1,ht):
            v=views[z]
            v[inside]=mat[inside]
            if z%step in (1,2):v[windows]=ink('566f6e') if z>2 else accent
            if z%step==0:v[rim]=tint(body,.83)
        roof=views[ht];roof[inside]=light;roof[rim]=tint(body,.77);roof[north|left]=tint(light,1.05)
        # Recessed roof, service rooms and small cylindrical rooftop water tanks.
        ys,xs=np.where(inside)
        if len(xs)<18:continue
        anchor=rng.randrange(len(xs));ax,ay=xs[anchor]+x0,ys[anchor]+y0
        center=(x0+int(np.mean(xs)),y0+int(np.mean(ys)))
        cx,cy=center
        if inside[cy-y0,cx-x0] and x1-x0>6 and y1-y0>6:
            rw=max(1,min(8,(x1-x0)//6));rh=max(1,min(6,(y1-y0)//6))
            cuboid(cx-rw,cy-rh,ht+1,cx+rw,cy+rh,ht+2,accent)
            cuboid(cx-rw,cy-rh,ht+3,cx+rw,cy+rh,ht+3,tint(accent,1.16))
        if len(xs)>90 and fid%3==0:
            # Corrugated rooftop extension, with alternating ridges and a warm fascia.
            ex,ey=xs[len(xs)//3]+x0,ys[len(xs)//3]+y0
            rw=max(2,min(9,(x1-x0)//5));rh=max(2,min(6,(y1-y0)//5))
            metal=ink(rng.choice(['588d87','70999c','a96c51','8aaba0']))
            cuboid(ex-rw,ey-rh,ht+1,ex+rw,ey+rh,ht+2,metal)
            for v in range(ey-rh,ey+rh+1,3):
                cuboid(ex-rw,v,ht+3,ex+rw,v,ht+3,tint(metal,1.10))
        if len(xs)>45:
            size=1 if unit>1 else 2
            for z in range(ht+1,ht+4):disc(z,ax,ay,size,ink('8d9b93'))
            disc(ht+4,ax,ay,size,ink('ccd1bc'))
    for x,y,r in treepoints:
        if vol[2,y,x]:continue
        h=rng.randrange(r+1,r+5)
        for z in range(1,h):disc(z,x,y,1,ink('746a4b'))
        leaf=ink(rng.choice(['689956','709e5a','82a958','598e63','90aa56','66915c']))
        for j in range(2*r+1):
            dz=j-r; radius=math.sqrt(max(0,r*r-dz*dz))
            c=tint(leaf,.74+.37*j/(2*r))
            disc(h-2+j,x,y,radius,c)
            if j>r and radius>=2:disc(h-2+j,x-1,y-1,radius*.53,tint(c,1.07))
    def layerline(z,p,w,c):
        im=Image.fromarray(vol[z].view('int32'),'I')
        ImageDraw.Draw(im).line(p,fill=c,width=w,joint='curve')
        vol[z]=np.asarray(im)
    deck=9
    for p,w,t in raised:
        for z in range(deck-2,deck+1):layerline(z,p,w+3,ink('73877c') if z<deck else ink('d8cca8'))
        layerline(deck,p,w,ink('85908a'))
        for x,y,dx,dy in along(p,8,1):layerline(deck,[(round(x),round(y)),(round(x+dx*3),round(y+dy*3))],1,ink('eed597'))
        for x,y,dx,dy in along(p,42,12):
            for z in range(1,deck-2):disc(z,round(x),round(y),max(2,w//4),ink('9aab98'))
        for x,y,dx,dy in along(p,31,6):cars.append((round(x+dy*w*.18),round(y-dx*w*.18),dx,dy,deck))
    if slug=='bridge':
        # The pale steel arch and vertical hangers follow the river span's road alignment.
        for y in range(61,189):
            u=(y-61)/127; roadway=220+int(3*math.sin(u*math.pi))
            arch=deck+round(34*math.sin(math.pi*u)**.85)
            for side in [-1,1]:
                post=roadway+side*8
                if y%12==2:
                    for z in range(deck+1,arch):disc(z,post,y,0,ink('cdd4bd'))
                for z in range(arch,arch+3):disc(z,post,y,1,ink('f3e9ca') if z==arch+2 else ink('b9beaa'))
                if y%20==5:layerline(arch,[(roadway-8,y),(roadway+8,y)],1,ink('d7d9c0'))
    def car(x,y,dx,dy,base):
        if not(3<=x<n-3 and 3<=y<n-3):return
        if base==0 and vol[1,y,x]:return
        clr=ink(rng.choice(['c96f50','e8c46f','e1d6b7','63878d','ae745e','d6decb']))
        ax,ay=round(dx*2),round(dy*2)
        for j in range(-2,3):
            xx,yy=round(x+dx*j),round(y+dy*j)
            disc(base+1,xx,yy,1,clr)
        disc(base+2,x,y,1,ink('516c70'));disc(base+3,x,y,1,clr)
    for c in cars:car(*c)
    if slug=='dingxi':
        x,y=192,160
        for z in range(1,7):
            cuboid(x-9,y-4,z,x+9,y+4,z,ink('718c86') if z>2 else ink('e0cc9a'))
        cuboid(x-10,y-5,7,x+10,y+5,8,ink('78a99c'));cuboid(x-10,y-5,9,x+10,y+5,9,ink('a3c8ad'))
        cuboid(x+11,y-1,1,x+12,y,10,ink('686a57'));cuboid(x+10,y-2,11,x+13,y+1,14,ink('e3aa5d'))
    if slug=='lehua':
        for x,y in stalls:
            c=ink(rng.choice(['c6765d','d7a85c','698f8b','bb7958']))
            cuboid(x-2,y-1,1,x+2,y+1,2,ink('987e62'))
            for z in (3,4):disc(z,x-2,y,0,ink('6b705b'));disc(z,x+2,y,0,ink('6b705b'))
            cuboid(x-3,y-2,5,x+3,y+2,5,c);cuboid(x-2,y-1,6,x+2,y+1,6,tint(c,1.15))
    used=np.where(vol.any(axis=(1,2)))[0][-1]+1
    # Crop each transparent layer. Pack into multiple sheets for mobile texture limits.
    frames=[]; sheet=None; sx=sy=rowh=0;number=-1; filenames=[]
    def save():
        if sheet is not None:sheet.crop((0,0,1024,sy+rowh)).save(ASSETS/f'{slug}-{number}.png',optimize=True)
    for z in range(used):
        img=rgba(vol[z]);bb=img.getbbox()
        if not bb:frames.append(None);continue
        a,b,c,d=bb;w=c-a;h=d-b
        if sx+w>1024:sx=0;sy+=rowh;rowh=0
        if sheet is None or sy+h>2048:
            save();number+=1;sx=sy=rowh=0;sheet=Image.new('RGBA',(1024,2048))
            filenames.append(f'{slug}-{number}.png')
        sheet.paste(img.crop(bb),(sx,sy));frames.append([number,sx,sy,w,h,a,b]);sx+=w;rowh=max(rowh,h)
    save()
    (ASSETS/f'{slug}.json').write_text(json.dumps({'size':n,'unit':unit,'center':data['center'],'sheets':filenames,'frames':frames},separators=(',',':')))
    print(slug,n,used,len(filenames),flush=True)

if __name__=='__main__':
    for scene in ('bridge','dingxi','lehua'):build(scene)
