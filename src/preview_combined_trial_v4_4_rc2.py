"""Render actual combined-coupon geometry; orange is illustrative, not an AMS color."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_combined_trial_v4_4_rc2 import ROOT,VERSION,parts,v
from support_removal_guide import render

BLUE=(72,150,180);ORANGE=(235,140,45)
FONT=ImageFont.load_default(size=26);SMALL=ImageFont.load_default(size=20)

def main():
    specimens,_=parts();byname={q['name']:q for q in specimens}
    out=ROOT/f'models/v{VERSION}'
    items=[(v.meshof(v.box((256,256,.1),(0,0,-.2))),(241,244,246))]
    for q in specimens:
        for m,c in [(q['model'],BLUE)]+[(s,ORANGE) for s in q['supports']]:
            mesh=v.meshof(m);mesh.apply_translation(q['translation']);items.append((mesh,c))
    im=Image.new('RGB',(1400,1500),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,18),'V4.4 RC2 | ONE PLATE | 12 labeled test specimens',font=FONT,fill='#193247')
    d.text((25,55),'BLUE = KEEP   ORANGE = 10 modeled pull-out supports (REMOVE after printing)',font=SMALL,fill='#804327')
    d.text((25,86),'P2S / 0.4 / PLA Basic / 0.20 mm: 56m 31s, 22.57 g | NOT production parts',font=SMALL,fill='#193247')
    im.paste(render(items,[0,-.00001,1],(1280,1280)),(60,130))
    for q in specimens:
        bounds=v.meshof(q['model']).bounds+q['translation'];x=bounds[:,0].mean();y=bounds[0,1]-3
        d.text((60+17.5+x*1245/256,130+17.5+(256-y)*1245/256),q['name'],font=SMALL,fill='#193247',anchor='mt')
    d.text((25,1420),'A/B: DIMM slots   C1-C4: lid captures   Hxx: screw / pin holes   K1/K2: tray corners',font=SMALL,fill='#193247')
    d.text((25,1455),'Open the configured 3MF as a PROJECT. Keep all modeled supports. Also clear A/B paddle supports.',font=SMALL,fill='#804327')
    im.save(out/'plate-guide.png')

    im=Image.new('RGB',(1400,2020),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,15),'V4.4 RC2 | Support removal and hole identification',font=FONT,fill='#193247')
    d.text((25,55),'BLUE = KEEP   ORANGE = REMOVE | CAD illustration; not a printed result',font=SMALL,fill='#804327')
    b=byname['B'];c=byname['C1'];h=byname['H32']
    sections=[
      ('A/B fixed end: TWO pull pieces',b,[1.9,13,0],[14,23.5,7],[1,-.45,1.1],
       'Grip each orange piece and pull horizontally toward the SLOT CENTRE.'),
      ('A/B spring end: ONE pull piece',b,[133,27,0],[145.2,34,7],[-1,-.4,1.1],
       'Pull toward slot centre. Also remove conventional support under the OUTER paddle.'),
      ('C1-C4: ONE raised pull piece each',c,None,None,[1,-1,1.1],
       'Pull toward the engraved C label, along the base. Keep the upper capture and lower pillar.')]
    for j,(title,q,lo,hi,cam,note) in enumerate(sections):
        y=110+j*480;d.text((25,y),title,font=FONT,fill='#193247')
        model=q['model'];supports=q['supports']
        if lo is not None:
            crop=v.box(np.array(hi)-lo,lo);model=model^crop;supports=[s^crop for s in supports if (s^crop).volume()>.001]
        im.paste(render([(v.meshof(model),BLUE)]+[(v.meshof(s),ORANGE) for s in supports],cam,(660,355)),(20,y+38))
        im.paste(render([(v.meshof(model),BLUE)],cam,(660,355)),(720,y+38))
        d.text((25,y+400),'Before removal',font=SMALL,fill='#804327');d.text((725,y+400),'Cleaned reference',font=SMALL,fill='#193247')
        d.text((25,y+435),note,font=SMALL,fill='#193247')
    y=1570;d.text((25,y),'H31 / H32 / H33 / H36: same nominal diameter for both holes',font=FONT,fill='#193247')
    im.paste(render([(v.meshof(h['model']),BLUE)],[.4,-1,.6],(660,300)),(20,y+40))
    im.paste(render([(v.meshof(h['model']),BLUE)],[.4,-1,-.8],(660,300)),(720,y+40))
    d.text((25,y+350),'SIDE hole: 5.7 mm nominal blind depth',font=SMALL,fill='#193247')
    d.text((725,y+350),'UNDERSIDE hole: 5.3 mm nominal blind depth',font=SMALL,fill='#193247')
    d.text((25,1970),'No support inside H holes. Test 6-32 screws gently; do not force a screw against the blind end.',font=SMALL,fill='#804327')
    im.save(out/'support-removal.png')
    print(out)

if __name__=='__main__':main()
