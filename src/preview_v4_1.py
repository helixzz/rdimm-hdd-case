"""Render actual V4.1 CAD and nominal support paths; no user photos."""
import json
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
import build_v4_1 as design
from support_removal_guide import render
from audit_v3_2_toolpaths import parse


def main(version='4.1-rc1',process='p1'):
    global design
    if version=='4.1-rc2':
        import build_v4_1_rc2 as design
    elif version=='4.2':
        import build_v4_2 as design
    elif version=='4.3':
        import build_v4_3 as design
    design.configure();p,_,_=design.base.parts();v=design.v;root=design.base.ROOT
    out=root/f'models/v{version}'
    blue=(72,150,180);orange=(235,145,45)
    font=ImageFont.load_default(size=22);small=ImageFont.load_default(size=17)
    im=Image.new('RGB',(1400,1000),'#fafafa');d=ImageDraw.Draw(im)
    d.text((20,15),'V'+version+' | reinforced candidate | CAD geometry, not impact validation',font=font,fill='#193247')
    views=[('Flat capture and matching lid tongue',[(p['body-pin-clearance']^v.box((11,23,7),(0,0,19)),blue),(p['lid-slide-lift']^v.box((11,23,7),(0,0,19)),orange)],[1,-.8,1.3]),
        ('Lid underside: four broad tongues',[(p['lid-slide-lift'],orange)],[1,-.7,-1.5]),
        ('1.0 mm DIMM spring + R1 root',[(p['tray-top-3']^v.box((10,24,8),(137,12,0)),blue)],[1,-.6,1.3]),
        (('Floor-grown R3.5 blend + rounded ledge' if version=='4.3' else 'Floor-grown R6 concave transition') if version in ('4.2','4.3') else 'Long-wall triangular belt below tray entry',[(p['body-pin-clearance']^v.box((70,12,15),(15,0,0)),blue)],[1,-.8,1.3])]
    for i,(title,objs,cam) in enumerate(views):
        x=10+(i%2)*700;y=70+(i//2)*440
        d.text((x+10,y),title,font=font,fill='#193247')
        im.paste(render([(v.meshof(s),c) for s,c in objs],cam,(680,400)),(x,y+30))
    d.text((20,965),'PRESS / slide 8 mm / LIFT. Follow the version compatibility guide. Remove supports before operation.',font=small,fill='#804327')
    im.save(out/'reinforcement-preview.png')
    records=json.loads((out/'verification.json').read_text())['plate_records']
    project_version=version if version in ('4.2','4.3') else version+'-'+process
    segs=parse(root/f'build/v{project_version}-projects/1-pin-clearance/plate_1.gcode')
    supports=segs[segs[:,7]==1]
    poses=next(r for r in records if r['stem'].endswith('plate-1-pin-clearance'))['poses']
    transforms={r['part']:np.array(r['assembly_to_plate']) for r in poses}
    guide=Image.new('RGB',(1400,1823 if version in ('4.2','4.3') else 1480),'#fafafa');d=ImageDraw.Draw(guide)
    d.text((20,15),'V'+version+' | BLUE: KEEP    ORANGE: REMOVE support',font=font,fill='#193247')
    d.text((20,48),'Actual nominal slicer beads; cleaned model on the right. No support-removal force prediction.',font=small,fill='#804327')
    regions=[('Body flat capture: remove support below upper ledge','body-pin-clearance',[0,7.5,20.8],[9,14.5,26],[1,-.65,.7]),
             ('Lid tongue, upside down: keep BOTH tongue and riser','lid-slide-lift',[2.8,7.5,22],[9,14.5,26],[1,-.65,-1.1]),
             ('Lid release: keep beam and R1 root','body-pin-clearance',[45,0,19.5],[79,3,26],[.25,-1,.7]),
             ('Bottom DIMM release: clear below beam before flexing','body-pin-clearance',[137,18.5,2],[147,39,11],[1,-.65,.9])]
    if version in ('4.2','4.3'):
        traysegs=parse(root/f'build/v{version}-projects/2-upper-trays/plate_1.gcode')
        traypose=next(r for r in records if r['stem'].endswith('plate-2-upper-trays'))['poses'][0]
        transforms[traypose['part']]=np.array(traypose['assembly_to_plate'])
        regions.append(('Upper tray: KEEP the 3 mm solid anchor; remove tooth/paddle support','tray-middle-3',[138,14,0],[145.4,33.5,7],[1,-.65,.9]))
    for i,(title,name,lo,hi,cam) in enumerate(regions):
        inv=np.linalg.inv(transforms[name]);blocks=[]
        region_supports=traysegs[traysegs[:,7]==1] if name.startswith('tray') else supports
        for x,y,qx,qy,z,w,h,_ in region_supports:
            mid=np.array([(x+qx)/2,(y+qy)/2,z-h/2,1])
            local=(inv@mid)[:3]
            if not(np.all(local>=lo) and np.all(local<=hi)):continue
            length=np.hypot(qx-x,qy-y)
            if length<1e-6:continue
            b=trimesh.creation.box(extents=[length,w,h])
            b.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(qy-y,qx-x),[0,0,1]))
            b.apply_translation(mid[:3]);b.apply_transform(inv);blocks.append(b)
        assert blocks,title
        model=v.meshof(p[name]^v.box(np.array(hi)-lo,lo))
        support=trimesh.util.concatenate(blocks)
        y=88+i*343;d.text((20,y),title,font=font,fill='#193247')
        guide.paste(render([(model,blue),(support,orange)],cam,(680,300)),(10,y+30))
        guide.paste(render([(model,blue)],cam,(680,300)),(710,y+30))
    guide.save(out/'support-removal.png')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',choices=['4.1-rc1','4.1-rc2','4.2','4.3'],default='4.1-rc1')
    parser.add_argument('--process',default='p1')
    args=parser.parse_args();main(args.version,args.process)
