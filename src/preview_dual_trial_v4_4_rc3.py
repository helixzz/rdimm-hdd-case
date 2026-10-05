"""Source-derived interface and removal diagrams, with illustrative role colors."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from build_dual_trial_v4_4_rc3 import ROOT, VERSION, parts, v
from support_removal_guide import render

BLUE=(72,150,180); ORANGE=(235,140,45); WHITE=(235,232,206)
FONT=ImageFont.load_default(size=26); SMALL=ImageFont.load_default(size=20)

def colored(q, crop=None, shifted=False):
    items=[]
    for objects,color in [([q['model']],BLUE),(q['cores'],ORANGE),(q['interfaces'],WHITE)]:
        for m in objects:
            if crop is not None: m=m^crop
            if m.volume()<.0001: continue
            mesh=v.meshof(m)
            if shifted: mesh.apply_translation(q['translation'])
            items.append((mesh,color))
    return items

def main():
    specimens=parts(); out=ROOT/f'models/v{VERSION}'
    im=Image.new('RGB',(1400,1500),'#fafafa'); d=ImageDraw.Draw(im)
    d.text((25,18),'V4.4 RC3 | ONE PLATE | PLA + Support For PLA',font=FONT,fill='#193247')
    d.text((25,55),'BLUE = KEEP PLA | ORANGE = REMOVE PLA | CREAM = REMOVE Support For PLA',font=SMALL,fill='#804327')
    d.text((25,88),'Role colors are illustrative. Printed PLA bodies and pull pieces use the SAME filament.',font=SMALL,fill='#193247')
    items=[(v.meshof(v.box((256,256,.1),(0,0,-.2))),(241,244,246))]
    for q in specimens: items+=colored(q,shifted=True)
    im.paste(render(items,[0,-.00001,1],(1280,1280)),(60,130))
    for q in specimens:
        bounds=v.meshof(q['model']).bounds+q['translation']; x=bounds[:,0].mean(); y=bounds[0,1]-3
        d.text((60+17.5+x*1245/256,130+17.5+(256-y)*1245/256),q['name'],font=SMALL,fill='#193247',anchor='mt')
    # Slicer-generated prime tower is not part of this CAD view.
    d.text((25,1395),'CAD layout excludes the slicer-generated prime tower. KEEP the tower in the print project.',font=SMALL,fill='#804327')
    d.text((25,1430),'P2S / 0.4 / 0.20 mm: 1h 03m 43s, 22.86 g including flushing | 10 filament changes',font=SMALL,fill='#193247')
    d.text((25,1465),'A = DIMM slot | C1 / C3 = long / short capture | H32 = selected 3.2 mm holes',font=SMALL,fill='#193247')
    im.save(out/'plate-guide.png')

    im=Image.new('RGB',(1400,1610),'#fafafa'); d=ImageDraw.Draw(im)
    d.text((25,15),'V4.4 RC3 | Remove PLA cores AND dedicated interfaces',font=FONT,fill='#193247')
    d.text((25,55),'BLUE = KEEP | ORANGE + CREAM = REMOVE | Actual CAD, not a printed result',font=SMALL,fill='#804327')
    lookup={q['name']:q for q in specimens}
    sections=[('A fixed end: TWO cores',lookup['A'],[1.9,13,0],[14,23.5,7],[1,-.45,1.1],
               'Pull toward SLOT CENTRE. Remove cream interfaces at roof, seat and grip foot.'),
              ('A spring end: ONE core',lookup['A'],[133,27,0],[145.2,34,7],[-1,-.4,1.1],
               'Pull toward SLOT CENTRE. Also remove automatic support under the outer paddle.'),
              ('C1 / C3: ONE core each, wider grip',lookup['C1'],None,None,[1,-1,1.1],
               'Pull toward the engraved C label along the base. Remove both upper and lower interfaces.')]
    for j,(title,q,lo,hi,cam,note) in enumerate(sections):
        y=115+j*480; d.text((25,y),title,font=FONT,fill='#193247')
        crop=v.box(np.array(hi)-lo,lo) if lo is not None else None
        m=q['model'] if crop is None else q['model']^crop
        im.paste(render(colored(q,crop),cam,(660,355)),(20,y+38))
        im.paste(render([(v.meshof(m),BLUE)],cam,(660,355)),(720,y+38))
        d.text((25,y+400),'Before removal: cream contact layers separate PLA surfaces',font=SMALL,fill='#804327')
        d.text((725,y+400),'Cleaned reference',font=SMALL,fill='#193247')
        d.text((25,y+435),note,font=SMALL,fill='#193247')
    d.text((25,1570),'Hold the rigid body, not the spring. Stop if a grip cracks. Physical removal force is unverified.',font=SMALL,fill='#804327')
    im.save(out/'support-removal.png'); print(out)

if __name__=='__main__': main()
