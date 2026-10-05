"""Exact CAD plate and dedicated-support removal views for v4.4."""
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_v4_4 import ROOT,parts,v
from support_removal_guide import render

BLUE=(72,139,180);CREAM=(224,196,130)

def main(version="4.4",part_factory=parts):
    parts=part_factory
    plates,_=parts();out=ROOT/f'models/v{version}';font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=19)
    report=json.loads((ROOT/f'build/v{version}-projects/slicing-report.json').read_text())
    audits=json.loads((ROOT/f'build/v{version}-projects/toolpath-audit.json').read_text())['plates']
    im=Image.new('RGB',(1600,1050),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,15),f'V{version} | COMPLETE SET | 2 plates / 4 permanent parts / 8 DIMMs',font=font,fill='#193247')
    d.text((25,57),'BLUE: permanent PLA | CREAM: dedicated Support For PLA | GREY: prime tower footprint',font=small,fill='#804327')
    for i,(label,items) in enumerate(plates):
        x=25+800*i;scene=[(v.meshof(v.box((256,256,.1),(0,0,-.2))),(239,242,245))]
        for q in items:
            scene.append((v.meshof(q['model']),BLUE));scene.extend((v.meshof(s),CREAM) for s in q['interfaces'])
        a,b=np.array(audits[i]['whole_plate']['tower_xy_bounds']);scene.append((v.meshof(v.box([*(b-a),.1],[*a,0])),(135,139,147)))
        d.text((x,102),f'PLATE {i+1}: '+('Body + lid' if i==0 else 'Middle tray + top tray'),font=font,fill='#193247')
        im.paste(render(scene,[0,-.00001,1],(750,750)),(x,145))
        r=report['results'][i];sec=round(r['seconds']);g=sum(f['total_used_g'] for f in r['filaments'])
        d.text((x,915),f'{sec//3600}h {sec%3600//60:02}m {sec%60:02}s | {g:.2f} g | {r["changes"]} changes',font=font,fill='#193247')
    d.text((25,978),'CAD reference. Ordinary automatic PLA supports are NOT shown; inspect Studio Line type > Support.',font=small,fill='#804327')
    d.text((25,1010),'Open the configured 3MF as a PROJECT. Keep material assignments, support paint and the prime tower.',font=small,fill='#193247');im.save(out/'plate-guide.png')
    body=plates[0][1][0];tray=plates[1][1][0]
    im=Image.new('RGB',(1500,1620),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,15),f'V{version} | Dedicated supports | CAD reference, NOT a printed result',font=font,fill='#193247')
    d.text((25,55),'Keep BLUE. Remove CREAM. Tools may be needed for fixed ends and lid captures.',font=small,fill='#804327')
    cases=[('Body / fixed DIMM end',body,0,[1,-.5,1.1],'Pull into the empty DIMM slot. Hold the rigid frame; do not pry on the roof.'),
           ('Body / moving DIMM end',body,1,[-1,-.5,1.1],'Pull into the empty DIMM slot. Keep the spring, tooth, paddle and root.'),
           ('Body / lid capture',body,4,[1,-1,1.1],'Pull inward, toward the case centre. Keep the upper capture flange.'),
           ('Upper tray / fixed end',tray,0,[1,-.5,1.1],'Same solid support at all tray ends. Clear all blocks before installing DIMMs.')]
    for i,(title,q,index,camera,note) in enumerate(cases):
        y=100+i*370;inv=np.array(q['inverse'])[:3,:];keep=q['model'].transform(inv);s=q['interfaces'][index].transform(inv)
        lo,hi=np.array(s.bounding_box()).reshape(2,3);lo-=np.array([1.8,1.5,3.]);hi+=np.array([2.,1.5,1.8])
        crop=v.box(hi-lo,lo);keep=keep^crop
        d.text((25,y),title,font=font,fill='#193247')
        im.paste(render([(v.meshof(keep),BLUE),(v.meshof(s),CREAM)],camera,(700,265)),(15,y+40))
        im.paste(render([(v.meshof(keep),BLUE)],camera,(700,265)),(770,y+40))
        d.text((25,y+310),'Before removal',font=small,fill='#804327');d.text((780,y+310),'Clean reference',font=small,fill='#193247')
        d.text((25,y+342),note,font=small,fill='#193247')
    d.text((25,1585),'Ordinary automatic PLA supports elsewhere also require removal. Mounting holes have NO support.',font=small,fill='#804327')
    im.save(out/'support-removal.png');print(f'Saved v{version} CAD guides',flush=True)

if __name__=='__main__':main()
