"""Extract three small ODbL scene datasets from the Taiwan OSM Parquet snapshot."""
import argparse, json, math
from pathlib import Path
import duckdb, shapely
from shapely import affinity
from shapely.geometry import box
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('parquet_dir', type=Path, help='Directory containing the five elements/part-*.parquet files')
source=str(parser.parse_args().parquet_dir / 'part-*.parquet')
# x points east, y south. Each local coordinate is one art pixel.
scenes=[('bridge',121.51585,25.01845,1.65,480),('dingxi',121.51547,25.01400,.72,380),('lehua',121.51341,25.00887,.67,380)]
for name,lon,lat,unit,n in scenes:
    sx=111320*math.cos(math.radians(lat))/unit
    sy=-110820/unit
    clip=box(0,0,n-1,n-1)
    a=lon-n/2/sx;b=lon+n/2/sx;c=lat+n/2/sy;d=lat-n/2/sy
    rows=duckdb.sql(f"""select id,tags,geom_wkb from read_parquet(?)
                 where x0<{b} and x1>{a} and y0<{d} and y1>{c} and typ in ('way','node') order by id""",params=[source]).fetchall()
    out=[]
    for fid,t,wkb in rows:
        keys=['highway','natural','waterway','building','building:levels','height','bridge','tunnel','leisure','landuse','sport','railway','amenity','layer','lanes','ref','tree_lined','name']
        tags={k:t[k] for k in keys if k in t}
        if not any(k in tags for k in ['highway','natural','waterway','building','leisure','landuse','sport','railway','amenity']):continue
        geom=shapely.from_wkb(wkb)
        if geom.geom_type=='Point' and tags.get('natural')!='tree' and tags.get('railway')!='subway_entrance':continue
        geom=affinity.affine_transform(geom,[sx,0,0,sy,n/2-sx*lon,n/2-sy*lat])
        if not geom.is_valid:geom=shapely.make_valid(geom)
        if tags.get('waterway')=='river' and geom.geom_type=='LineString':
            geom=geom.buffer(69/unit)
            tags['natural']='water'
        geom=geom.intersection(clip).simplify(.43,preserve_topology=True)
        for g in shapely.get_parts(geom):
            if g.is_empty or g.geom_type not in ('Polygon','LineString','Point'):continue
            coords=g.exterior.coords if g.geom_type=='Polygon' else g.coords
            out.append([fid,tags,g.geom_type,[[round(x,1),round(y,1)] for x,y in coords]])
    dest=ROOT/'tools'/'geodata';dest.mkdir(exist_ok=True)
    (dest/(name+'.json')).write_text(json.dumps({'center':[lon,lat],'unit':unit,'size':n,'features':out},ensure_ascii=False,separators=(',',':')))
    print(name,len(out),sum('building' in t for i,t,typ,xy in out))
