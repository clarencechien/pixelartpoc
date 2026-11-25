"""Illustrated building envelopes, street furniture and four Yonghe landmarks."""
import math
import random

import numpy as np
import shapely as geo
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Point, Polygon
from shapely.ops import split
from shapely.geometry import LineString

TAU=2*math.pi
WALLS=['e1c69f','d2bea6','e2bc94','c79680','c6cab9','e0d0ac','b9c8bb','c8b79b']
METAL=['438b82','5f898e','ae6352','789591','8e9b81','a95b48','578586']
TILE=['b85f46','ab5541','bc7052','8f6850']
SHOP=['bf5944','367d76','c6924e','4e8999','a47454']

def shade(c,f):
    if isinstance(c,str):c=bytes.fromhex(c)
    return tuple(min(255,round(v*f)) for v in c)

class Frame:
    """Transform local X (frontage) and Y (front) into the district plane."""
    def __init__(self,x,y,angle=0):
        self.x,self.y=x,y
        self.c,self.s=math.cos(angle),math.sin(angle)
        self.angle=angle
    def at(self,u,v,z):
        return self.x+u*self.c-v*self.s,self.y+u*self.s+v*self.c,z

class Artist:
    def __init__(self,tri,quad,block,stack,group,decal,out):
        self.tri,self.quad,self.block,self.stack,self.group=tri,quad,block,stack,group
        self.decal=decal
        self.lettering=Image.new('RGB',(256,256))
        self.atlas_path=out/'signs.png'
        self.sign_rows={}

    def box(self,f,u,v,z,w,d,h,tone,mat=0):
        self.block(*f.at(u,v,z),w,d,h,tone,f.angle,mat)

    def face(self,f,points,c,mat=0):
        self.quad(*(f.at(*p) for p in points),c,mat)

    def tube(self,a,b,r,tone,sides=6):
        axis=np.subtract(b,a,dtype=float);length=np.linalg.norm(axis)
        if length<.05:return
        axis/=length
        u=np.cross(axis,[1.,0.,0.] if abs(axis[2])>.9 else [0.,0.,1.])
        u/=np.linalg.norm(u);v=np.cross(axis,u)
        offsets=[r*(math.cos(i*TAU/sides)*u+math.sin(i*TAU/sides)*v) for i in range(sides)]
        self.stack([a+p for p in offsets],[b+p for p in offsets],tone,True)

    def cylinder(self,f,u,v,profile,tone,sides=8):
        last=None
        for z,r in profile:
            ring=[f.at(u+r*math.cos(i*TAU/sides),v+r*math.sin(i*TAU/sides),z) for i in range(sides)]
            if last:self.stack(last,ring,tone,z==profile[-1][0])
            last=ring

    def shell(self,g,z0,z1,wall,roof,material,seed):
        if z1<=z0:return
        for facet in geo.get_parts(geo.constrained_delaunay_triangles(g)):
            self.tri(*[(x,y,z1) for x,y in list(facet.exterior.coords)[:3]],roof,2)
        for loop in [g.exterior,*g.interiors]:
            pts=list(loop.coords)
            for (x,y),(u,v) in zip(pts,pts[1:]):
                a=math.atan2(v-y,u-x)
                self.quad((x,y,z0),(u,v,z0),(u,v,z1),(x,y,z1),shade(wall,.83+.16*math.cos(a+.7)),material,round(a%TAU*255/TAU),seed)

    def gable(self,f,u,v,z,w,d,rise,c):
        # Two corrugated slopes, closed ends and a real ridge.
        for side in (-1,1):
            self.face(f,[(u-w/2,v+d*side/2,z),(u+w/2,v+d*side/2,z),(u+w/2,v,z+rise),(u-w/2,v,z+rise)],shade(c,.82 if side<0 else 1.07),3)
        for side in (-1,1):
            x=u+side*w/2
            self.tri(f.at(x,v-d/2,z),f.at(x,v+d/2,z),f.at(x,v,z+rise),shade(c,.72))
        self.box(f,u,v,z+rise-.12,w,.42,.30,shade(c,1.18))

    def fitted_roof(self,g,frame,eave,peak,tone):
        # Split at the ridge before triangulation; concave footprints and courtyards stay open.
        ys=[(y-frame.y)*frame.c-(x-frame.x)*frame.s for x,y in g.exterior.coords]
        lo,hi=min(ys),max(ys)
        mid=(lo+hi)/2;half=max(.1,(hi-lo)/2)
        ridge=LineString([frame.at(-500,mid,0)[:2],frame.at(500,mid,0)[:2]])
        def roofpoint(x,y):
            v=(y-frame.y)*frame.c-(x-frame.x)*frame.s
            return x,y,eave+(peak-eave)*max(0,1-abs(v-mid)/half)
        for piece in split(g,ridge).geoms:
            if piece.area<.2:continue
            u,v=piece.representative_point().coords[0]
            c=shade(tone,.82 if (v-frame.y)*frame.c-(u-frame.x)*frame.s<mid else 1.08)
            for facet in geo.get_parts(geo.constrained_delaunay_triangles(piece)):
                self.tri(*(roofpoint(x,y) for x,y in list(facet.exterior.coords)[:3]),c,3)
            pts=list(piece.exterior.coords)
            for (x,y),(a,b) in zip(pts,pts[1:]):
                self.quad((x,y,eave),(a,b,eave),roofpoint(a,b),roofpoint(x,y),shade(tone,.73))

    def awning(self,f,u,v,z,w,depth,c,striped=False):
        count=max(3,min(11,round(w/.85))) if striped else 1
        for j in range(count):
            a=u-w/2+j*w/count;b=a+w/count
            pigment='f0d5a2' if striped and j%2 else c
            self.face(f,[(a,v,z),(b,v,z),(b,v+depth,z-.55),(a,v+depth,z-.55)],pigment)
            self.face(f,[(a,v+depth,z-.55),(b,v+depth,z-.55),(b,v+depth,z-.94),(a,v+depth,z-.94)],shade(pigment,.78))

    def sign(self,f,u,v,z,text,w,h,bg,fg):
        self.box(f,u,v-.17,z,w,.38,h,bg)
        if text not in self.sign_rows:
            row=len(self.sign_rows)*48
            if row+48>256:raise ValueError('Full sign atlas')
            self.sign_rows[text]=row
            tile=Image.new('RGB',(252,46),'#'+bg)
            ink=ImageDraw.Draw(tile)
            ink.rectangle((2,2,249,43),outline='#'+fg,width=1)
            font=ImageFont.truetype('NotoSansCJK-Bold.ttc',37,index=3)
            ink.text((126,22),text,font=font,fill='#'+fg,anchor='mm',stroke_width=0)
            self.lettering.paste(tile,(2,row+1))
        row=self.sign_rows[text]
        uv=[(3,row+2),(251,row+2),(251,row+45),(3,row+45)]
        for side,d in [(1,v+.28),(-1,v-.66)]:
            self.decal([f.at(u-side*w/2,d,z+h),f.at(u+side*w/2,d,z+h),
                        f.at(u+side*w/2,d,z),f.at(u-side*w/2,d,z)],uv)

    def save_signs(self):
        self.lettering.save(self.atlas_path,optimize=True)

def apartment(art,fid,t,g,h,road,close):
    rnd=random.Random(fid)
    seed=fid%256
    x,y=g.centroid.coords[0]
    art.group(x,y,5)
    pts=list(g.exterior.coords);street=road.interpolate(road.project(g.centroid))
    # Choose the longest exposed frontage facing the nearest mapped street.
    def rank(pair):
        (x0,y0),(x1,y1)=pair
        return math.hypot(x1-x0,y1-y0)/(3+math.hypot((x0+x1)/2-street.x,(y0+y1)/2-street.y))
    (ax,ay),(bx,by)=max(zip(pts,pts[1:]),key=rank)
    w=math.hypot(bx-ax,by-ay);a=math.atan2(by-ay,bx-ax)
    f=Frame((ax+bx)/2,(ay+by)/2,a)
    check=f.at(0,.45,0)
    if g.contains(Point(*check[:2])):f=Frame(f.x,f.y,a+math.pi)
    center=g.representative_point();r=g.boundary.distance(center)
    rf=Frame(center.x,center.y,a)
    wall=rnd.choice(WALLS);roof=rnd.choice(['cfc7a8','b8b7a0','cac7b7','cec1a5'])
    metal=rnd.choice(METAL);terrace=None
    if h>28 and r>3.8:
        # A street-level podium, narrower upper floorplate, then a stepped crown.
        step=g.buffer(-min(r*.23,2),join_style='mitre')
        if step.geom_type=='Polygon' and step.area>20:terrace=step
    def lower_shell(zend):
        if close and w>5.8 and zend>4.8 and street.distance(g)<14 and seed%3!=0:
            cut=Polygon([f.at(u,v,0)[:2] for u,v in [(-w*.48,.6),(w*.48,.6),(w*.48,-2.1),(-w*.48,-2.1)]])
            base=g.difference(cut)
            for part in geo.get_parts(base):
                if part.geom_type=='Polygon':art.shell(part,0,3.6,shade(wall,.77),roof,4,seed)
            for u in np.linspace(-w*.44,w*.44,max(2,round(w/4.2))):
                art.box(f,u,-.34,0,.58,.66,3.65,shade(wall,.9))
            art.shell(g,3.6,zend,wall,roof,4,seed)
        else:art.shell(g,0,zend,wall,roof,4,seed)
    coping_height=h
    if terrace is not None:
        glass=h>41 and seed%3!=0
        upper=rnd.choice(['749b9c','6e9698','83a3a6','779691']) if glass else wall
        podium=min(h*.27,12)
        lower_shell(podium)
        coping_height=podium
        crown=terrace.buffer(-min(1.8,r*.17),join_style='mitre')
        top=h-3.6 if crown.geom_type=='Polygon' and crown.area>12 else h
        art.shell(terrace,podium,top,upper,roof,5 if glass else 4,seed)
        if top<h:art.shell(crown,top,h,shade(upper,.88),roof,5 if glass else 4,seed)
        if r>6:
            art.box(rf,0,0,h,min(7,r),min(4,r*.6),2,'819996')
            for k in range(3):art.box(rf,0,-1+k,h+2,min(7,r),.28,.65,'c1c2a7')
    elif h<12.6 and r>1.7 and seed%4!=0:
        eave=max(2.1,h-min(3.1,1+r*.25))
        lower_shell(eave)
        art.fitted_roof(g,rf,eave,h,rnd.choice(TILE) if seed%3 else metal)
    else:
        setback=g.buffer(-min(1.4,r*.23),join_style='mitre') if r>3 and h>12 and seed%3==0 else None
        top=h-2.65 if setback is not None and setback.geom_type=='Polygon' and setback.area>12 else h
        lower_shell(top)
        coping_height=top
        if top<h:art.shell(setback,top,h,shade(wall,.93),roof,4,seed)
        if r>4 and seed%5==0:
            # A shaded rooftop terrace, timber slats and a planted edge.
            tw=min(9,r*1.4);td=min(6,r)
            art.box(rf,0,0,h,tw,td,.28,'b89267')
            for u in [-tw*.43,tw*.43]:
                for v in [-td*.41,td*.41]:art.box(rf,u,v,h+.28,.32,.32,2.15,'805d49')
            for u in np.linspace(-tw*.5,tw*.5,7):art.box(rf,u,0,h+2.4,.48,td+.2,.28,'a5805a')
            art.box(rf,0,td*.44,h+.28,tw*.70,.85,.74,'6e9364')
        elif r>2 and seed%5 not in (1,4):
            wid=min(10,r*1.65);depth=min(6,r*1.24)
            art.box(rf,0,0,h,wid*.91,depth*.91,1.4,shade(metal,.77))
            art.gable(rf,0,0,h+1.38,wid,depth,min(1.95,depth*.25),metal)
    # Circular water tanks, alternating horizontal bands and caps are modelled at street zoom.
    art.group(x,y,6)
    if r>3.8 and seed%3!=0:
        tx=r*.75;ty=-r*.47
        art.cylinder(rf,tx,ty,[(h,.55),(h+.55,.55),(h+.56,1.05),(h+1.97,1.05),(h+2.35,.48)],'afbcb4')
    if close and h>9 and g.area>45 and seed%3!=0:
        for p,q in zip(pts,pts[1:]):
            dx,dy=q[0]-p[0],q[1]-p[1]
            # Put coping on the first terrace when a tower has a setback.
            deck_h=coping_height
            if h>=12.6 and dx*dx+dy*dy>1:
                art.block((p[0]+q[0])/2,(p[1]+q[1])/2,deck_h,math.hypot(dx,dy),.36,.65,shade(wall,1.08),math.atan2(dy,dx))
    if w<3.7:return
    if w>6.5 and h>10 and seed%3!=0:
        # Rounded balcony slabs with a raised outer balustrade and a shaded recess.
        length=min(8.6,w*.70);depth=min(1.75,length*.24)
        for z in np.arange(4,min(h-1,28 if close else 17),3.6 if close else 6.6):
            edge=[(-length*.5,-.22),(length*.5,-.22),(length*.5,depth*.56),(length*.40,depth),(-length*.40,depth),(-length*.5,depth*.56)]
            lo=[f.at(u,v,z) for u,v in edge];hi=[f.at(u,v,z+.44) for u,v in edge]
            art.stack(lo,hi,'ddd1ad',True)
            art.box(f,0,depth-.15,z+.45,length*.77,.27,.76,rnd.choice(['94a99a','baab8a','a8bcb0']))
            if close and int(z)%3!=0:
                art.box(f,-length*.22,depth-.54,z+.45,length*.33,.6,.57,'a87956')
                art.box(f,-length*.22,depth-.54,z+.97,length*.37,.7,.43,'648759')
    if close or seed%4==0:
        if street.distance(g.boundary)<19 and seed%3!=0:
            span=min(10,w*.91)
            art.awning(f,0,.12,3.55,span,min(2.2,span*.29),rnd.choice(SHOP),seed%3==1)
            if close and seed%5==0:
                art.box(f,w*.34,.65,4.2,.62,1.55,2.8,rnd.choice(SHOP))

def temple_roof(a,f,y,z,w,d,h):
    """A swept hip roof with lifted corners, two tile slopes and a shortened ridge."""
    def point(t,u,side):
        x=u*(w/2-t*d*.32)
        v=y+side*d*.5*(1-t)
        crown=h*(.18*t+.82*t*t)
        return f.at(x,v,z+crown+(abs(u)**4)*(2.08-.65*t))
    for side in [-1,1]:
        for j in range(28):
            l=-1+j/14;r=l+1/14
            for k in range(4):
                t=k/4;nt=(k+1)/4
                tone=['c8753e','dc944f','c77c42','d88e4d'][j%4]
                a.quad(point(t,l,side),point(t,r,side),point(nt,r,side),point(nt,l,side),shade(tone,.88 if side<0 else 1.06))
            p,q=point(0,l,side),point(0,r,side)
            a.quad(p,q,(q[0],q[1],q[2]-.65),(p[0],p[1],p[2]-.65),'2f8877')
            a.tube(p,q,.27,'f1be68')
        for side_x in [-1,1]:
            a.tri(point(0,side_x,side),point(1,side_x,side),f.at(w*.5*side_x,y,z+1.0),'ad5f35')
            ridge=[point(t/8,side_x,side) for t in range(9)]
            for p,q in zip(ridge,ridge[1:]):a.tube(p,q,.32,'e8b955')
    end=w/2-d*.32
    ridge=[f.at(u*end,y,z+h+1.47*abs(u)**4) for u in np.linspace(-1,1,17)]
    for p,q in zip(ridge,ridge[1:]):a.tube(p,q,.43,'efbd63')
    # Swallowtail finials and a pair of ceramic animal silhouettes on the ridge.
    for side in [-1,1]:
        for offset,color in [(0,'378d80'),(.47,'c86d40')]:
            path=[f.at(side*(end+dx),y+offset,z+h+dz) for dx,dz in [(-2,1.2),(0,1.65),(1.25,2.45),(2.0,3.6),(2.35,4.65)]]
            for p,q in zip(path,path[1:]):a.tube(p,q,.35,color)
        path=[f.at(side*dx,y,z+h+dz) for dx,dz in [(2,1.1),(3,2.5),(4.3,2.9),(5.3,2.0),(6.5,2.5),(7.2,3.7),(6.4,4.25)]]
        for p,q in zip(path,path[1:]):a.tube(p,q,.42,'3e9589')
        a.cylinder(f,side*6.6,y,[(z+h+3.75,.65),(z+h+4.35,.44)],'ce7345')
    a.cylinder(f,0,y,[(z+h+.1,.65),(z+h+1.35,.95),(z+h+2.1,.45)],'ca7049')

def temple(a,f):
    a.group(f.x,f.y,5)
    a.box(f,0,0,.0,39,46,.8,'bca88b')
    for j in range(4):a.box(f,0,20.0-j*.67,j*.27,28,2.4,.35,'dac9a7')
    # Three halls face south. The central hall rises over two side galleries.
    for y,w,d,z,h in [(-13,32,16,11.0,4.1),(1,35,15,8.5,4.1),(13,34,11,6.8,3.2)]:
        a.box(f,0,y-.9,.8,w-5,d-3,z-1.6,'a65237')
        a.box(f,0,y+d*.5-2.2,1,w-5,.26,z-2.25,'613e32')
        for u in np.linspace(-(w-5)/2,(w-5)/2,7):
            a.cylinder(f,u,y+d*.5-1.25,[(.8,.83),(1.3,.83),(1.5,.56),(z-.4,.56),(z-.14,.81)],'ad4935')
            for base in [1.35,z-1.18]:a.cylinder(f,u,y+d*.5-1.25,[(base,.63),(base+.3,.64)],'dbb268')
        a.box(f,0,y+d*.5-1.1,z-1.25,w-1,1.1,.62,'3d8175')
        temple_roof(a,f,y,z,w,d,h)
    a.box(f,0,-13,14.7,18,6.9,1.8,'a34d33')
    temple_roof(a,f,-13,16.3,23,11.8,4.0)
    for side in [-1,1]:
        a.box(f,side*17.5,-1,.8,3.5,25,4.8,'ab5b44')
        a.gable(Frame(*f.at(side*17.6,-1,0)[:2],f.angle+math.pi/2),0,0,5.6,25,5,1.3,'b97944')
    a.sign(f,0,18.0,4.35,'保福宮',9.4,2.25,'2b5953','ffe0a0')
    # Painted brackets and lattice door panels are visible beneath the front eave.
    for u in [-12,-8,-4,0,4,8,12]:
        a.box(f,u,16.82,5.85,2.45,.95,.45,'278071')
        a.box(f,u,17.09,6.28,3.03,1.15,.36,'ba6b3e')
        a.box(f,u,17.23,6.64,3.5,1.36,.23,'e4b46b')
        if u!=0:
            a.box(f,u,16.45,1.2,2.2,.23,3.8,'683d34')
            for v in [-.72,0,.72]:a.box(f,u+v,16.64,1.45,.15,.20,3.2,'c18c55')
    for u in [-5.15,5.15]:
        previous=None
        for j in range(21):
            angle=j*TAU/10
            p=f.at(u+math.cos(angle)*.65,17.3+math.sin(angle)*.65,1.4+j*.22)
            if previous is not None:a.tube(previous,p,.22,'aeaa87')
            previous=p
    for side in [-1,1]:
        u=side*11.5
        a.box(f,u,20.9,.8,2.4,2.15,.85,'a99f85')
        a.cylinder(f,u,20.9,[(1.65,.78),(2.3,.91),(2.72,.63),(3.25,.73),(3.55,.41)],'938e78')
        a.box(f,u,21.55,2.75,.66,.64,.44,'aaa186')
    for u in [-12,-8,8,12]:
        a.cylinder(f,u,18.1,[(4.0,.34),(4.3,.76),(5.1,.83),(5.55,.41)],'c94e36')
        a.cylinder(f,u,18.1,[(3.65,.13),(4.05,.18)],'e9b957')
    a.cylinder(f,0,19.7,[(1.1,.65),(1.65,.78),(2,1.38),(2.7,1.55),(2.93,1.28)],'817b57')

def station(a,f):
    a.group(f.x,f.y,5)
    a.box(f,0,0,.08,7.8,16,.45,'d6c6a3')
    for i in range(11):a.box(f,0,5.7-i*.58,.50,5.5,.65,.19+i*.16,'9da9a3')
    # Barrel vault: solid curved panels separated by steel ribs, open at the street end.
    for side in [-1,1]:
        a.box(f,side*3.35,-1,.5,.48,13,2,'77928d')
        for v in [-6,-2,2,5.5]:a.box(f,side*3.35,v,1,.35,.38,3.6,'587975')
    for j in range(12):
        t0,t1=math.pi*j/12,math.pi*(j+1)/12
        def pt(t,v):return f.at(3.95*math.cos(t),v,3.75+2.5*math.sin(t))
        a.quad(pt(t0,-7.8),pt(t1,-7.8),pt(t1,6.5),pt(t0,6.5),shade('86beb4',.74+.24*math.sin(t0)))
        for v in [-7.8,-3.2,1.5,6.5]:a.tube(pt(t0,v),pt(t1,v),.19,'e0debf')
    a.sign(f,0,6.75,3.36,'頂溪站',6.9,1.48,'2e5655','fff0bc')
    a.box(f,4.8,6.35,0,.6,.6,7.3,'5a6961')
    a.sign(f,4.8,6.6,5.25,'2',2.0,2.05,'d58a32','fff2cb')

def market(a,paths,mask,entrance):
    rng=random.Random(424)
    for g in paths:
        for dist in np.arange(2,g.length,6.3):
            p=g.interpolate(dist)
            if not mask.contains(p):continue
            q=g.interpolate(min(dist+1,g.length))
            heading=math.atan2(q.y-p.y,q.x-p.x)
            for side in [-1,1]:
                angle=heading if side==-1 else heading+math.pi
                f=Frame(p.x-side*math.sin(heading)*3.85,p.y+side*math.cos(heading)*3.85,angle)
                a.group(f.x,f.y,5)
                tint=rng.choice(['c24c3f','de9d36','428e82','527c9c','cb7146'])
                a.box(f,0,0,.18,4.45,2.5,1.,'a46e4a')
                a.box(f,0,.84,1.18,4.5,.85,.20,'dcc99e')
                a.awning(f,0,-1.65,3.65,5.05,3.65,tint,True)
                for u in (-2.1,2.1):a.box(f,u,-1.2,.2,.21,.21,3.34,'605b49')
                a.group(f.x,f.y,6)
                for u in [-1.25,-.4,.45,1.3]:
                    a.cylinder(f,u,.9,[(1.4,.34),(1.74,.27)],rng.choice(['db9d47','a64a37','77a45b']))
                a.cylinder(f,1.76,1.66,[(2.0,.26),(2.23,.47),(2.77,.47),(2.96,.24)],'cf5037')
    x,y=entrance;a.group(x,y,5)
    f=Frame(x,y,-1.36)
    for u in [-5.0,5.0]:
        a.box(f,u,0,0,.65,.75,6.3,'497968');a.box(f,u,0,0,1.0,1.1,.9,'cfb88e')
    a.sign(f,0,.35,5.0,'樂華夜市',11.8,2.85,'983f35','ffe9a5')
    a.box(f,0,0,7.86,12.4,1.18,.38,'e2ac54')
    for u in [-4.7,-3.4,3.4,4.7]:a.cylinder(f,u,0,[(4.15,.29),(4.5,.41),(4.93,.24)],'db6c3e')

def bridge(a,start,end,carriageways):
    # Trace the two road centrelines through the curved span. The two ribs converge at one end.
    def edges(t):
        y=start[1]+t*(end[1]-start[1]);hits=[]
        for path,width,tags in carriageways:
            if tags.get('name')!='中正橋':continue
            for p,q in zip(path.coords,list(path.coords)[1:]):
                if min(p[1],q[1])<=y<=max(p[1],q[1]) and abs(q[1]-p[1])>.01:
                    x=p[0]+(q[0]-p[0])*(y-p[1])/(q[1]-p[1])
                    hits.extend([x-width/2,x+width/2])
        if not hits:
            x=start[0]+t*(end[0]-start[0]);hits=[x-11,x+11]
        return min(hits),max(hits),y
    def rib(t,side):
        l,r,y=edges(t);width=r-l
        merge=min(1,max(0,(t-.33)/.54));merge=merge*merge*(3-2*merge)
        x=(l if side<0 else r)*(1-merge)+(l+width*.24+side*.42)*merge
        return x,y,10+43*math.sin(math.pi*t)**.82
    for side in [-1,1]:
        path=[rib(j/60,side) for j in range(61)]
        for p,q in zip(path,path[1:]):
            a.group(*p[:2],5);a.tube(p,q,1.28,'f0efdb',8)
        for j in range(1,25):
            t=j/25;l,r,y=edges(t);p=rib(t,side);q=(l if side<0 else r,y,10.5)
            a.group(*p[:2],5);a.tube(p,q,.30,'bacdc6',4)
        for j in range(40):
            l,r,y=edges(j/40);ll,rr,yy=edges((j+1)/40)
            x=l-1 if side<0 else r+1;xx=ll-1 if side<0 else rr+1
            a.group(x,y,5);w=side*2.2
            a.quad((x,y,10.2),(xx,yy,10.2),(xx+w,yy,10.2),(x+w,y,10.2),'c9ab85')
            a.tube((x+w,y,11.25),(xx+w,yy,11.25),.23,'7d9b8d')
            if j%3==0:
                a.tube((x+w,y,10.2),(x+w,y,14.1),.21,'62817b')
                a.block(x+w*.85,y,14.05,1.2,.7,.28,'ecdab1')
    for j in range(2,11):
        t=j/14;p,q=rib(t,-1),rib(t,1)
        if math.dist(p,q)>2:
            a.group(*p[:2],5);a.tube(p,q,.47,'d0dacc')
            a.tube(p,rib(t+.04,1),.27,'bfcfc4',4)
