"""CAD + nominal slicer support removal map for the A/B trial."""
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont
from build_support_trial_v4_4 import ROOT,VERSION,parts,v
from support_removal_guide import render
from audit_v3_2_toolpaths import parse


def main():
    result,_=parts();blue=(72,150,180);orange=(235,140,45)
    im=Image.new('RGB',(1400,1660),'#fafafa');pen=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=19)
    pen.text((20,15),'V4.4 RC1 | ONE PLATE, two single-slot coupons | NOT production trays',font=font,fill='#193247')
    pen.text((20,52),'BLUE = KEEP   ORANGE = REMOVE (manual pull pieces + automatic supports)',font=small,fill='#804327')
    segs=parse(ROOT/f'build/v{VERSION}-projects/0-support-ab/plate_1.gcode');segs=segs[segs[:,7]==1]
    for i,name in enumerate(('A','B')):
        model,supports=result[name];dy=25 if name=='A' else 80
        auto=[]
        for x,y,qx,qy,z,w,h,_ in segs:
            mid=np.array([(x+qx)/2-54.5,(y+qy)/2-dy,z-h/2])
            if not(0<=mid[0]<=147 and 1.8<=mid[1]<=35.6):continue
            length=np.hypot(qx-x,qy-y)
            if length<1e-6:continue
            b=trimesh.creation.box([length,w,h]);b.apply_transform(trimesh.transformations.rotation_matrix(np.arctan2(qy-y,qx-x),[0,0,1]));b.apply_translation(mid);auto.append(b)
        items=[(v.meshof(model),blue)]+[(v.meshof(s),orange) for s in supports]
        if auto:items.append((trimesh.util.concatenate(auto),orange))
        y=95+i*280
        pen.text((20,y),name+(' | current slot + pull supports' if name=='A' else ' | same pull supports + local residue relief'),font=font,fill='#193247')
        im.paste(render(items,[.1,-1,1.9],(1360,230)),(20,y+30))
    model,supports=result['B']
    for j,(title,lo,hi,cam) in enumerate([
        ('Fixed end: grip each of TWO orange pieces; pull toward slot centre',[1.9,13.,0],[14.,23.5,7],[1,-.45,1.1]),
        ('Spring end: grip ONE orange piece; pull toward slot centre',[133.,27.,0],[145.2,34.,7],[-1,-.4,1.1])]):
        crop=v.box(np.array(hi)-lo,lo);y=700+j*420
        pen.text((20,y),title,font=font,fill='#193247')
        objs=[(v.meshof(model^crop),blue)]+[(v.meshof(s^crop),orange) for s in supports if (s^crop).volume()>.001]
        im.paste(render(objs,cam,(660,350)),(20,y+40))
        im.paste(render([(v.meshof(model^crop),blue)],cam,(660,350)),(720,y+40))
    pen.text((20,1570),'Left: before removal. Right: cleaned reference. Pull horizontally inward; do not pry against the clip.',font=small,fill='#193247')
    pen.text((20,1605),'Also remove conventional paddle support. Clear ALL orange pieces before inserting a DIMM.',font=small,fill='#804327')
    im.save(ROOT/f'models/v{VERSION}/support-removal.png')


if __name__=='__main__':main()
