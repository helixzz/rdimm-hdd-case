"""Whole-product batch render with the sliced tower footprint."""
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import evaluate_product_batch as batch
from support_removal_guide import render
from preview_dual_trial_v4_4_rc3 import colored

def main():
    f=batch.f;plates,_=f.make_parts(True,True);body,lid=plates[0][1];middle,top=plates[1][1]
    bounds=np.array(middle['model'].bounding_box()).reshape(2,3);a,b=bounds[1,:2]-bounds[0,:2];gap=4.;margin=(256-a-b-gap)/2
    layout=[(0,[margin,margin]),(90,[margin+a+gap,margin]),(180,[margin+b+gap,margin+a+gap]),(270,[margin,margin+b+gap])]
    groups=[('2-bodies',[batch.place(body,0,[54.5,20],'a'),batch.place(body,0,[54.5,130],'b')]),
            ('2-lids',[batch.place(lid,0,[56.3,20],'a'),batch.place(lid,0,[56.3,130],'b')]),
            ('4-trays',[batch.place(q,ang,xy,str(i)) for i,(q,(ang,xy)) in enumerate(zip([middle,top,middle,top],layout))])]
    im=Image.new('RGB',(1530,650),'#fafafa');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=18)
    d.text((20,15),'TWO COMPLETE CASES / THREE PLATES | research layout',font=font,fill='#193247')
    d.text((20,52),'Blue: product   Orange + cream: removable supports   Grey: actual sliced tower footprint',font=small,fill='#193247')
    for i,(label,items) in enumerate(groups):
        shapes=[(f.v.meshof(f.v.box((256,256,.1),(0,0,-.2))),(230,235,239))]
        for q in items:shapes+=colored(q)
        audit=json.loads((f.OUT/'batch-two'/label/'whole-plate-audit.json').read_text());bb=audit['tower_xy_bounds']
        if bb:
            lo,hi=np.array(bb);shapes.append((f.v.meshof(f.v.box([*(hi-lo),.1],[*lo,0])),(125,130,140)))
        im.paste(render(shapes,[0,-.00001,1],(500,500)),(10+i*510,95))
        d.text((20+i*510,590),label.replace('-',' '),font=font,fill='#193247')
    d.text((20,625),'By-layer printing. Nozzle/gantry collision, warpage and physical removal still need real validation.',font=small,fill='#804327')
    im.save(f.OUT/'batch-layout.png')

if __name__=='__main__':main()
