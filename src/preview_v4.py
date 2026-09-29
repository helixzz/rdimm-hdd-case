"""Mesh-derived V4 overview and actual slicer support removal reference."""
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
from build_v4 import ROOT,parts,v3,rc,SATA_Y
from support_removal_guide import render
from audit_v3_2_toolpaths import parse


def main(version='4.0-rc1',depth=6.,side_marks=True):
    import build_v4 as base
    base.VERSION=version;base.SATA_DEPTH=depth
    base.SIDE_MARKS=side_marks
    p,_,_=parts();out=ROOT/('models/v'+version)
    blue=(76,159,181);orange=(233,136,48);green=(64,120,82)
    im=Image.new('RGB',(1440,1170),'#fafafa');d=ImageDraw.Draw(im)
    title=ImageFont.load_default(size=28);font=ImageFont.load_default(size=19)
    d.text((25,15),f'V{version.upper()} | 8 bare DDR5 RDIMMs | 147 x 101.6 x 26 mm',font=title,fill='#193247')
    d.text((25,55),'CAD preview. New full assembly is NOT physically validated.',font=font,fill='#804327')
    body=v3.meshof(p['body-pin-clearance'])
    im.paste(render([(body,blue)],[1,-.7,1.6],(700,440)),(15,100))
    d.text((25,90),'Integrated bottom: 2 slots; external release access',font=font,fill='#193247')
    low=v3.meshof(p['body-pin-clearance']^v3.box((147,101.6,8)))
    im.paste(render([(low,blue)],[-1,-.45,-1.1],(700,440)),(730,100))
    d.text((750,90),'UNDERSIDE: one corrected SATA recess',font=font,fill='#193247')
    exploded=[(body,blue)]
    for name,z in [('tray-middle-3',35.),('tray-top-3',56.),('lid-slide-lift',57.)]:
        s=p[name].translate((0,0,z));exploded.append((v3.meshof(s),orange if name.startswith('tray') else blue))
    im.paste(render(exploded,[1,-1,1.1],(700,530)),(10,580))
    d.text((25,550),'4 pieces: bottom body + middle 3 + top 3 + lid',font=font,fill='#193247')
    openlid=v3.meshof(p['lid-slide-lift'].translate((0,-8,12)))
    im.paste(render([(body,blue),(openlid,orange)],[-1,-.75,1.6],(700,530)),(730,580))
    d.text((750,550),'PRESS, slide 8 mm, then LIFT; reverse to close',font=font,fill='#193247')
    d.text((25,1130),'Supports REQUIRED. Print full set once, verify loading and dock fit, then repeat.',font=font,fill='#804327')
    im.save(out/'v4-overview.png')
    # New integrated flexure has supports below its foot, which must be removed.
    segs=parse(ROOT/f'build/v{version}-projects/1-pin-clearance/plate_1.gcode')
    segs=segs[segs[:,7]==1].copy();segs[:,[0,2]]-=54.5;segs[:,[1,3]]-=20.
    guide=Image.new('RGB',(1440,1110),'#fafafa');gd=ImageDraw.Draw(guide)
    gd.text((25,15),f'V{version.upper()} | BLUE: keep model    ORANGE: remove supports',font=title,fill='#193247')
    gd.text((25,55),'Actual nominal support paths. Do not cut the long beam, tooth or lower PCB shelf.',font=font,fill='#193247')
    views=[('Bottom release / outside',[136,18.7,0],[147,39.7,12],[1,-.45,.7]),
           ('Fixed PCB hood / inside',[1.6,30,4],[10,42,11],[1,-.3,.9]),
           ('SATA recess / underside',[0,SATA_Y,0],[depth+2,SATA_Y+47,8],[-1,-.3,-.9])]
    for i,(label,lo,hi,camera) in enumerate(views):
        model=v3.meshof(p['body-pin-clearance']^v3.box(np.array(hi)-lo,lo));blocks=[]
        for x,y,qx,qy,z,w,h,_ in segs:
            mid=np.array([(x+qx)/2,(y+qy)/2,z-h/2])
            if not np.all(mid>=lo) or not np.all(mid<=hi):continue
            length=np.hypot(qx-x,qy-y)
            if length<1e-6:continue
            b=trimesh.creation.box(extents=[length,w,h])
            b.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(qy-y,qx-x),[0,0,1]));b.apply_translation(mid);blocks.append(b)
        support=trimesh.util.concatenate(blocks)
        y=95+i*330;gd.text((25,y),label,font=font,fill='#193247')
        guide.paste(render([(model,blue),(support,orange)],camera,(690,290)),(10,y+25))
        guide.paste(render([(model,blue)],camera,(690,290)),(735,y+25))
    guide.save(out/'v4-support-removal.png')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='4.0-rc1')
    parser.add_argument('--depth',type=float,default=6.)
    parser.add_argument('--no-side-marks',action='store_true')
    args=parser.parse_args();main(args.version,args.depth,not args.no_side_marks)
