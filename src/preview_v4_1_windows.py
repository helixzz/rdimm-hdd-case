"""Render actual old/new end walls; keep supplied user photos private."""
from PIL import Image,ImageDraw,ImageFont
import build_v4_1_rc2 as design
from support_removal_guide import render


def main():
    v=design.v
    design.previous.configure();old,_,_=design.base.parts()
    design.configure();new,_,_=design.base.parts()
    im=Image.new('RGB',(1400,820),'#fafafa');d=ImageDraw.Draw(im)
    title=ImageFont.load_default(size=26);font=ImageFont.load_default(size=19)
    d.text((20,15),'V4.1 RC2 | closed upper wall, accessible lower release windows',font=title,fill='#193247')
    crop=v.box((11,101.6,26),(136,0,0))
    for i,(label,p) in enumerate([('RC1: openings continue to the top',old),('RC2: 45-degree shoulders + R1 apex',new)]):
        x=i*700
        d.text((x+20,70),label,font=font,fill='#193247')
        im.paste(render([(v.meshof(p['body-pin-clearance']^crop),(72,150,180))],[1,-.18,.32],(680,430)),(x+10,100))
    d.text((35,560),'Lower access preserved: Z 2.2 - 10.8 mm',font=title,fill='#193247')
    d.text((35,605),'Continuous upper link: minimum 4.11 mm high; original wall thickness 1.6 mm',font=font,fill='#193247')
    d.text((35,642),'RC1 lid and both upper trays are unchanged and reusable.',font=font,fill='#193247')
    d.text((35,690),'Configured p2 project: no support above Z10.8 in either window.',font=font,fill='#804327')
    d.text((35,727),'Supports below the release beams and other catches must still be removed.',font=font,fill='#804327')
    d.text((35,775),'CAD preview. Physical access, arch finish and impact performance remain unverified.',font=font,fill='#804327')
    im.save(design.base.ROOT/'models/v4.1-rc2/window-preview.png')


if __name__=='__main__':main()
