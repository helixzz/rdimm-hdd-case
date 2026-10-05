"""Dimensioned schematic for the RC4 long-wall floor transition."""
import math
from PIL import Image,ImageDraw,ImageFont
from build_v4 import ROOT


def main():
    im=Image.new('RGB',(1050,650),'#fafafa');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=22);small=ImageFont.load_default(size=18)
    def p(y,z):return (110+50*y,590-40*z)
    d.text((30,20),'RC4 | R2 long-wall floor fillet | dimensions in mm',font=font,fill='#193247')
    d.text((30,55),'Schematic section; other internals omitted. Surface improvement not yet tested.',font=small,fill='#804327')
    d.polygon([p(0,0),p(12,0),p(12,4),p(1.6,4),p(1.6,11.8),p(0,11.8)],fill='#bcc7ce')
    arc=[(3.6+2*math.cos(t),6+2*math.sin(t)) for t in [(-math.pi/2)-i*math.pi/64 for i in range(33)]]
    d.polygon([p(1.6,4),p(3.6,4)]+[p(*q) for q in arc],fill='#e98830')
    d.line([p(*q) for q in arc],fill='#a85b19',width=3)
    d.rectangle([p(1.9,11.6),p(12,10.8)],fill='#4c9fb5')
    for z,label in [(4,'Floor: Z = 4'),(6,'Fillet top: Z = 6'),(10.8,'First removable tray: Z = 10.8')]:
        d.line([p(3.6,z),p(12,z)],fill='#81929d',width=1)
        d.text((740,p(12,z)[1]-13),label,font=small,fill='#193247')
    x=p(9,0)[0];top=p(0,10.8)[1];bottom=p(0,6)[1]
    d.line([(x,top),(x,bottom)],fill='#193247',width=2)
    for z,sgn in [(top,1),(bottom,-1)]:d.polygon([(x,z),(x-5,z+sgn*10),(x+5,z+sgn*10)],fill='#193247')
    d.text((x+15,(top+bottom)/2-12),'4.8 mm clearance',font=small,fill='#193247')
    d.text((p(4,0)[0],p(0,5.1)[1]),'R2 added here',font=font,fill='#a85b19')
    d.text((30,615),'Only two long edges. Original mounting bores are kept clear; short ends are unchanged.',font=small,fill='#193247')
    im.save(ROOT/'models/v4.0-rc4/floor-fillet-section.png')


if __name__=='__main__':main()
