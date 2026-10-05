"""Face-on CAD views of the physical version identifiers."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_v4_4_1 import ROOT,VERSION,parts,v
from support_removal_guide import render

def colored(model,name):
    mesh=v.meshof(model);z=.2 if name.startswith('body') else (25.8 if name.startswith('lid') else 6.6)
    face=mesh.vertices[mesh.faces];mask=np.max(abs(face[:,:,2]-z),axis=1)<.0001
    return [(mesh.submesh([np.flatnonzero(~mask)],append=True),(72,139,180)),
            (mesh.submesh([np.flatnonzero(mask)],append=True),(26,66,96))]

def main():
    plates,_=parts();im=Image.new('RGB',(1400,1150),'#fafafa');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=20)
    d.text((25,15),f'V{VERSION} | Physical identifiers | Exact CAD, not a printed sample',font=font,fill='#193247')
    for i,q in enumerate([q for _,items in plates for q in items]):
        x=25+(i%2)*700;y=70+(i//2)*540
        model=q['model'].transform(np.array(q['inverse'])[:3,:]);name=q['name']
        camera=[0,-.00001,-1] if name.startswith('body') else [0,-.00001,1]
        d.text((x,y),name,font=small,fill='#193247')
        im.paste(render(colored(model,name),camera,(650,310)),(x,y+35))
        if name.startswith('body'):lo,hi=[48,35,-.1],[86,41,1]
        elif name.startswith('lid'):lo,hi=[48,79,25.4],[85,84,26.1]
        else:
            lo,hi=[1.9,18,6.2],[6.3,80,6.9]
        crop=model^v.box(np.array(hi)-lo,lo)
        if 'tray' in name:crop=crop.rotate((0,0,-90));camera=[0,-.00001,1]
        im.paste(render(colored(crop,name),camera,(650,140)),(x,y+360))
    d.text((25,1120),'0.20 mm recess / 0.60 mm stroke. Recess floors shaded dark for clarity; bottom label reads from outside.',font=small,fill='#193247')
    im.save(ROOT/f'models/v{VERSION}/version-marks.png')

if __name__=='__main__':main()
