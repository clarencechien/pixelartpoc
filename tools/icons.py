"""Small original pixel illustrations for the landmark index and app icon."""
from PIL import Image,ImageDraw
from pathlib import Path
D=Path(__file__).resolve().parents[1]/'dist/assets'
for name in ['bridge','dingxi','lehua','baofu','logo']:
    im=Image.new('RGBA',(56,48));p=ImageDraw.Draw(im)
    def box(points,color):p.rectangle(points,fill=color)
    def poly(points,color):p.polygon(points,fill=color)
    def line(points,color,w=1):p.line(points,fill=color,width=w)
    if name=='bridge':
        poly([(2,35),(40,19),(54,24),(17,43)],'#81afa0')
        for x,y in [(9,35),(36,30),(21,38),(39,25)]:line([(x,y),(x+5,y-2)],'#bad6bd')
        poly([(3,27),(43,12),(54,17),(14,34)],'#656c59')
        for x,y in [(9,29),(44,16)]:poly([(x,y),(x+4,y-1),(x+4,y+5),(x+2,y+7),(x,y+6)],'#929a7f')
        line([(4,27),(44,12),(52,16)],'#c5bf9b',2)
        line([(12,31),(51,15)],'#e7dac0',2)
        for off,shade in [(0,'#9f9d82'),(6,'#f7ebc8')]:
            path=[(6+off,26),(9+off,18),(13+off,13),(18+off,10),(23+off,8),(28+off,8),(33+off,10),(39+off,15)]
            line(path,'#596953',3);line(path,shade,2)
            for x,y,bot in [(12,15,24),(19,11,21),(26,9,18),(32,10,16)]:line([(x+off,y+1),(x+off,bot)],shade)
    elif name=='dingxi':
        poly([(4,31),(31,20),(52,29),(24,42)],'#aaa98a')
        poly([(8,21),(30,12),(48,19),(25,30)],'#a0b88a')
        poly([(8,21),(25,28),(25,39),(8,32)],'#b29874')
        poly([(25,28),(48,18),(48,29),(25,39)],'#466e67')
        for x,y in [(28,28),(34,25),(40,22)]:poly([(x,y),(x+3,y-1),(x+3,y+4),(x,y+6)],'#a1c2ac')
        poly([(5,20),(29,9),(51,18),(26,30)],'#40716b')
        poly([(5,18),(29,7),(51,16),(26,27)],'#9bbba1')
        for x in range(3):line([(12+x*6,16-x*3),(30+x*6,23-x*3)],'#c1cba6')
        box((11,27,15,33),'#566c58');box((48,26,49,36),'#6e755e')
        box((45,19,52,26),'#b67e41');box((46,19,51,24),'#edb65a');box((48,20,49,23),'#f7e4a8')
    elif name=='lehua':
        poly([(4,34),(29,22),(51,31),(25,43)],'#a8aa87')
        for x,y in [(10,24),(24,30),(44,21)]:box((x,y,x+1,y+10),'#645a4a')
        poly([(8,28),(25,35),(46,26),(29,20)],'#f2d493')
        poly([(8,28),(25,35),(25,40),(8,33)],'#bd7b56')
        poly([(25,35),(46,26),(46,31),(25,40)],'#84684f')
        poly([(6,19),(29,9),(49,17),(25,28)],'#a86448')
        for k in range(5):
            x=6+4*k;y=19-2*k
            poly([(x,y),(x+5,y-2),(x+23,y+6),(x+19,y+9)],'#c9694d' if k%2==0 else '#f3d999')
        poly([(6,19),(25,27),(25,30),(6,22)],'#b1684e')
        for x,y in [(15,26),(36,24)]:box((x,y,x+3,y+4),'#e69c56');box((x+1,y-1,x+2,y),'#725939')
    elif name=='baofu':
        poly([(4,34),(29,23),(52,30),(26,43)],'#a9a98b')
        for x,y in [(13,26),(23,30),(34,27),(43,23)]:
            box((x,y,x+2,y+9),'#a3543f')
        for x,y in [(16,9),(9,18)]:
            roof=[(x-4,y+2),(x+2,y+4),(x+14,y-2),(x+24,y+1),
                  (x+28,y-2),(x+26,y+4),(x+14,y+10),(x-2,y+5)]
            poly(roof,'#be6c42')
            line(roof[:5],'#40776a',2)
            line(roof[5:],'#e5a456',2)
        box((23,29,28,31),'#365b4e')
    else:
        for off,c in [(7,'#83a990'),(3,'#aec998'),(0,'#f2e6b4')]:
            poly([(6,21+off),(27,10+off),(49,20+off),(28,31+off)],c)
        poly([(17,16),(22,13),(28,15),(22,19)],'#d59864')
        poly([(17,12),(22,9),(28,11),(22,15)],'#f4d3a0')
        poly([(17,12),(22,15),(22,19),(17,16)],'#c07958')
        poly([(22,15),(28,11),(28,15),(22,19)],'#b98f64')
        poly([(29,16),(34,14),(38,16),(34,19)],'#749976')
    im.save(D/(name+'-icon.png'))
