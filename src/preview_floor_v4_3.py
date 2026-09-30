"""Render actual V4.2/V4.3 sections, no illustrative invented geometry."""
from PIL import Image,ImageDraw,ImageFont
import build_v4_3 as d


def main():
    d.previous.configure();old,_,_=d.base.parts()
    d.configure();new,_,_=d.base.parts()
    roi=d.v.box((.2,9.,12.),(59.9,0,0))
    im=Image.new('RGB',(1300,850),'#fafafa');pen=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=23);small=ImageFont.load_default(size=18)
    pen.text((20,20),'V4.3 | actual CAD section at X = 60 mm | near long wall',font=font,fill='#193247')
    for i,(title,part) in enumerate([('V4.2: floor fillet only',old),('V4.3: floor-grown reinforcement + rounded ledge',new)]):
        ox=55+i*650;oy=710;s=43
        def xy(y,z):return (ox+y*s,oy-z*s)
        pen.text((20+i*650,75),title,font=small,fill='#193247')
        section=(part['body-pin-clearance']^roi).rotate((0,-90,0)).slice(60)
        for poly in section.to_polygons():pen.polygon([xy(y,-x) for x,y in poly],fill='#4896b4')
        pen.line([xy(0,10.8),xy(10,10.8)],fill='#cf8732',width=2)
        pen.text(xy(1,11.5),'First tray bottom Z10.8',font=small,fill='#805024')
        pen.text(xy(2,2),'Floor top Z4',font=small,fill='white')
        if i:
            pen.text(xy(4.7,8),'R3.5 blend',font=small,fill='#193247')
            pen.text(xy(4.7,10.2),'Top Z10.4 / R0.4 edge',font=small,fill='#193247')
        else:pen.text(xy(3,7),'R6',font=font,fill='#193247')
    pen.text((20,765),'0.4 mm vertical gap: ledge reinforces the wall, it is NOT a tray support surface.',font=small,fill='#193247')
    pen.text((20,800),'Mounting bores and loading paths preserved. Actual strength and print finish remain unverified.',font=small,fill='#804327')
    im.save(d.base.ROOT/'models/v4.3/floor-transition-preview.png')


if __name__=='__main__':main()
