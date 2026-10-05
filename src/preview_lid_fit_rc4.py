"""Source-backed RC4 replacement-lid and actual support-path preview."""
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
import build_v4_1_rc4 as design
from support_removal_guide import render
from audit_v3_2_toolpaths import parse


def main():
    design.previous.configure();old,_,_=design.base.parts()
    design.configure();new,_,_=design.base.parts()
    v=design.v;root=design.base.ROOT;out=root/'models/v4.1-rc4'
    blue=(72,150,180);orange=(235,145,45)
    im=Image.new('RGB',(1400,1100),'#fafafa');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=23);small=ImageFont.load_default(size=18)
    d.text((20,15),'V4.1 RC4 | replacement lid for existing RC1 / RC2 body',font=font,fill='#193247')
    crop=v.box((7.,8.,4.2),(2.8,7,22))
    for i,(label,p) in enumerate([('RC3: side relief starts at Z24.0',old),('RC4: continuous relief down to Z23.7',new)]):
        d.text((20+i*700,65),label,font=font,fill='#193247')
        im.paste(render([(v.meshof(p['lid-slide-lift']^crop),blue)],[1,.9,-1.2],(680,360)),(10+i*700,100))
    d.text((20,465),'Tongue stays 1.2 mm; root stays 1.4 mm. Neck relief returns via a short slope.',font=small,fill='#804327')
    d.text((20,495),'Side clearance remains 0.4 mm and extends lower. Flat bearing area stays 41.80 mm2.',font=small,fill='#804327')
    d.text((20,525),'297 lateral + upward pose checks pass. Printed fit, force and strength remain unverified.',font=small,fill='#804327')
    record=json.loads((out/'verification.json').read_text())['plate_records'][-1]
    inv=np.linalg.inv(np.array(record['poses'][0]['assembly_to_plate']))
    segs=parse(root/'build/v4.1-rc4-projects/3-replacement-lid/plate_1.gcode')
    blocks=[]
    for x,y,qx,qy,z,w,h,support in segs:
        if not support:continue
        mid=np.array([(x+qx)/2,(y+qy)/2,z-h/2,1]);local=(inv@mid)[:3]
        if not(np.all(local>=[2.8,7,22]) and np.all(local<=[9.8,15,26.2])):continue
        length=np.hypot(qx-x,qy-y)
        if length<1e-6:continue
        b=trimesh.creation.box(extents=[length,w,h]);b.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(qy-y,qx-x),[0,0,1]))
        b.apply_translation(mid[:3]);b.apply_transform(inv);blocks.append(b)
    assert blocks
    model=v.meshof(new['lid-slide-lift']^crop)
    d.text((20,575),'BLUE: KEEP / ORANGE: REMOVE support',font=font,fill='#193247')
    d.text((720,575),'Cleaned shape: keep the tongue and riser',font=font,fill='#193247')
    im.paste(render([(model,blue),(trimesh.util.concatenate(blocks),orange)],[1,.9,-1.2],(680,380)),(10,610))
    im.paste(render([(model,blue)],[1,.9,-1.2],(680,380)),(710,610))
    d.text((20,1020),'Only one lid needs printing. Clear all four tongue supports before fitting to the empty body.',font=small,fill='#193247')
    d.text((20,1055),'CAD and nominal beads; not a removal-force, distortion or impact simulation.',font=small,fill='#804327')
    im.save(out/'lid-fit-preview.png')


if __name__=='__main__':main()
