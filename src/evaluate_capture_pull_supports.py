"""Geometric study of inward-pull sacrificial pads under four lid captures.
Not a print release. Nominal clearances do not establish release force.
"""
import json
from pathlib import Path
import numpy as np
import build_v4_3 as d
from build_v4_1 import CAPTURES
v=d.v

def support(y,length):
    # Runners reduce contact area; continuous middle web keeps pad together.
    a=v.box((2.9,length-.6,.6),(3.4,y+.3,22.8))
    for yy in (y+.3,y+length-.9):
        a+=v.box((2.9,.6,1.4),(3.4,yy,22.4))
    # The raised inner grip clears the permanent flange and grows on a 45deg
    # underside. The narrowest nominal neck is 0.8 mm, not a break-away tab.
    points=[(6.2,22.4),(8.,24.2),(8.,25.6),(6.8,25.6),(6.8,23.8),(6.2,23.8)]
    a+=d.m.CrossSection([points]).extrude(2.4).rotate((90,0,0)).translate((0,y+length/2+1.2,0))
    assert len(a.decompose())==1
    return a

def parts():
    d.configure();p,_,_=d.base.parts();body=p['body-pin-clearance'];rows=[];pieces=[]
    for y,length in CAPTURES:
        for side in ('left','right'):
            a=support(y,length)
            if side=='right':a=a.mirror((1,0,0)).translate((147,0,0))
            for distance in np.linspace(0,10,51):
                d.base.clear(body,a.translate((float(distance)*(1 if side=='left' else -1),0,0)),('pull',side,y,distance))
            assert v.meshof(a).is_watertight
            pieces.append(a)
            rows.append({'side':side,'capture_y':y,'length':length,'extraction_poses':51,'tested_travel_mm':10,'support_volume_mm3':a.volume()})
    return body,pieces,rows

def main():
    out=d.base.ROOT/'build/capture-support-assessment';out.mkdir(exist_ok=True)
    body,pieces,rows=parts()
    from PIL import Image,ImageDraw,ImageFont
    from support_removal_guide import render
    im=Image.new('RGB',(1260,720),'#fafafa');pen=ImageDraw.Draw(im);font=ImageFont.load_default(size=23)
    pen.text((20,15),'Lid-capture support study | BLUE keep / ORANGE remove',font=font,fill='#193247')
    crop=v.box((10,18,7),(0,2,20))
    for x,items,label in [(10,[(v.meshof(body^crop),(72,150,180)),(v.meshof(pieces[0]),(235,140,45))],'Support runners + raised grip toward box interior'),(640,[(v.meshof(body^crop),(72,150,180))],'After removal: original lid channel unchanged')]:
        im.paste(render(items,[1,-1,1.2],(600,520)),(x,70))
        pen.text((x+10,610),label,font=ImageFont.load_default(size=18),fill='#193247')
    pen.text((20,655),'Pull toward box centre; do not lever against the upper flange. Geometry study, not yet printed.',font=ImageFont.load_default(size=20),fill='#193247')
    im.save(out/'capture-pull-support.png')
    report={'status':'unreleased geometric study','permanent_body_lid_geometry_unchanged':True,'nominal_runner_top_z':23.8,'nominal_runner_bottom_z':22.4,'flange_bottom_z':24.,'pillar_top_z':22.1,'pieces':rows,'physical_verified':False,'limits':'No thermal sag, grip strength or adhesion simulation. Must use local support blockers and check actual slicing before test printing.'}
    (out/'assessment.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
