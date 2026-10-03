"""Source-geometry and actual sliced tower diagrams for the RC4 test plate."""
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_trial_v4_4_rc4 import ROOT,VERSION,parts,v
from support_removal_guide import render
from preview_dual_trial_v4_4_rc3 import colored,BLUE

def main():
    qs,_=parts();out=ROOT/f'models/v{VERSION}';folder=ROOT/f'build/v{VERSION}-projects'
    report=json.loads((folder/'slicing-report.json').read_text());audit=json.loads((folder/'toolpath-audit.json').read_text())
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=19)
    im=Image.new('RGB',(1400,1500),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,16),'V4.4 RC4 | ONE PLATE / SIX SPECIMENS | PLA + Support For PLA',font=font,fill='#193247')
    d.text((25,57),'BLUE: keep PLA | ORANGE: remove PLA cores | CREAM: remove dedicated interfaces',font=small,fill='#804327')
    items=[(v.meshof(v.box((256,256,.1),(0,0,-.2))),(239,242,245))]
    for q in qs:items+=colored(q,shifted=True)
    a,b=np.array(audit['tower_xy_bounds']);items.append((v.meshof(v.box([*(b-a),.1],[*a,0])),(135,139,147)))
    im.paste(render(items,[0,-.00001,1],(1280,1280)),(60,100))
    for q in qs:
        bb=np.array(q['model'].bounding_box()).reshape(2,3)+q['translation'];x=bb[:,0].mean();y=bb[0,1]-3
        d.text((60+17.5+x*1245/256,100+17.5+(256-y)*1245/256),q['name'],font=font,fill='#193247',anchor='mt')
    d.text((25,1380),'Grey: actual sliced tower footprint. KEEP the tower and all modeled support parts.',font=small,fill='#804327')
    d.text((25,1415),'A: DIMM / C1,C3: captures / H32: holes / P1: baseline / P2: internal infill candidate',font=small,fill='#193247')
    seconds=round(report['estimated_seconds']);grams=sum(f['total_used_g'] for f in report['filaments'])
    d.text((25,1450),f'P2S / 0.4 / 0.20 mm | {seconds//3600}h {seconds%3600//60:02}m {seconds%60:02}s | {grams:.2f} g | {report["filament_changes"]} changes',font=small,fill='#193247')
    im.save(out/'plate-guide.png')
    im=Image.new('RGB',(1400,1580),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,15),'V4.4 RC4 | Removal guide | Actual CAD, not a printed result',font=font,fill='#193247')
    d.text((25,56),'BLUE stays. ORANGE + CREAM must be removed. The outer paddle gusset STAYS.',font=small,fill='#804327')
    lookup={q['name']:q for q in qs}
    rows=[('A / fixed end: TWO raised grips',lookup['A'],[6.2,13.9,0],[13.5,23.5,7],[1,-.5,1.1],
           'Pull into the slot (+X). Remove both upper and lower cream layers; no feet remain.'),
          ('A / spring end: ONE raised grip',lookup['A'],[133,27,0],[145.2,34,7],[-1,-.4,1.1],
           'Pull into the slot (-X). Keep the blue exterior 45-degree gusset and spring.'),
          ('C1 and C3 / ONE grip each',lookup['C1'],None,None,[1,-1,1.1],
           'Pull horizontally toward the C label (+X). Remove upper and lower cream layers.')]
    for i,(title,q,lo,hi,cam,note) in enumerate(rows):
        y=105+i*475;d.text((25,y),title,font=font,fill='#193247')
        crop=v.box(np.array(hi)-lo,lo) if lo else None
        keep=q['model'] if crop is None else q['model']^crop
        im.paste(render(colored(q,crop),cam,(660,350)),(20,y+35))
        im.paste(render([(v.meshof(keep),BLUE)],cam,(660,350)),(720,y+35))
        d.text((25,y+392),'Before removal (illustrative role colors)',font=small,fill='#804327')
        d.text((725,y+392),'After removal: reference shape',font=small,fill='#193247')
        d.text((25,y+427),note,font=small,fill='#193247')
    d.text((25,1540),'Hold the rigid body. Do not lever against the spring or the retaining roof. Stop if a grip starts to crack.',font=small,fill='#804327')
    im.save(out/'support-removal.png')

if __name__=='__main__':main()
