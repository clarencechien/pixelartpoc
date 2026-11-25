"""Small original pixel illustrations for the landmark index and app icon."""
from PIL import Image,ImageDraw
from pathlib import Path
D=Path(__file__).resolve().parents[1]/'dist/assets'
for name in ['bridge','dingxi','lehua','baofu','kawabata','renai','logo']:
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
        poly([(8,9),(26,4),(43,9),(27,15)],'#d9ccae')
        poly([(8,9),(27,15),(27,40),(8,33)],'#bcb39e')
        poly([(27,15),(43,9),(43,34),(27,40)],'#a59a86')
        for y in (14,20,26):
            for x in (12,18):box((x,y+(x-12)//3,x+3,y+3+(x-12)//3),'#647c7b')
            line([(29,y+3),(40,y-1)],'#647c7b',2)
        poly([(24,31),(44,24),(48,26),(27,34)],'#d9c793')
        poly([(28,33),(44,28),(44,34),(28,39)],'#374f50')
        box((46,24,47,35),'#767d73');box((44,21,50,25),'#466482')
    elif name=='kawabata':
        poly([(3,35),(42,19),(54,25),(17,41)],'#8bb6a6')
        for x,y in [(9,28),(24,22),(39,16)]:
            box((x,y,x+2,y+8),'#b5af94');box((x+6,y+1,x+8,y+8),'#a9a78c')
            line([(x+1,y+5),(x+4,y+2),(x+7,y+5)],'#c5bfa0',2)
        poly([(2,27),(44,10),(53,14),(11,31)],'#ddd0ac')
        line([(10,31),(53,14)],'#63786b',2)
        for x in range(7,48,5):box((x,26-(x-7)*2//5,x+1,29-(x-7)*2//5),'#a49d86')
    elif name=='renai':
        poly([(2,29),(31,12),(54,23),(25,41)],'#91ac76')
        p.ellipse((15,21,39,31),fill='#dbca9e')
        p.ellipse((18,23,36,29),fill='#94b879')
        for x,y in [(10,25),(17,21),(34,18),(42,21),(43,27)]:
            box((x,y,x+1,y+4),'#887958')
            p.ellipse((x-3,y-5,x+3,y+1),fill='#577e62')
        poly([(9,30),(16,26),(21,28),(14,33)],'#a5684d')
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
