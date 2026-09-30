"""Render the actual RC4/V4.2 first clip anchor geometry, no user photo."""
from PIL import Image,ImageDraw,ImageFont
import build_v4_2 as d
from support_removal_guide import render


def main():
    d.previous.configure();old,_,_=d.base.parts()
    d.configure();new,_,_=d.base.parts()
    crop=d.v.box((7.,13.,7.),(138.8,10.,-.1))
    im=Image.new('RGB',(1300,660),'#fafafa');pen=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=23);small=ImageFont.load_default(size=18)
    pen.text((20,20),'V4.2 | first clip anchor repair on BOTH upper trays',font=font,fill='#193247')
    for i,(title,p) in enumerate([('OLD: only 0.2 mm web behind pillar relief',old),('NEW: 3.0 mm anchor; R1 root transition',new)]):
        pen.text((20+650*i,75),title,font=small,fill='#193247')
        shape=p['tray-middle-3']^crop
        if i:
            extra=(new['tray-middle-3']-old['tray-middle-3'])^crop
            objects=[(d.v.meshof(shape-extra),(72,150,180)),(d.v.meshof(extra),(55,170,95))]
        else:objects=[(d.v.meshof(shape),(72,150,180))]
        im.paste(render(objects,[1.,-1.2,.8],(630,430)),(10+650*i,115))
    pen.text((20,570),'GREEN = added permanent model material. Do NOT remove as support.',font=font,fill='#237b3b')
    pen.text((20,610),'Tooth/paddle position unchanged. Beam 18 -> 15.2 mm; release force still needs physical validation.',font=small,fill='#804327')
    im.save(d.base.ROOT/'models/v4.2/tray-root-preview.png')


if __name__=='__main__':main()
