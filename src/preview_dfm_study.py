"""Before/after renders from the evaluated CAD, not generated photographs."""
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import evaluate_dfm_geometry as g
from support_removal_guide import render
from preview_dual_trial_v4_4_rc3 import colored

def main():
    old=g.dual.parts()[0];new=g.specimens('combined')[0]
    im=Image.new('RGB',(1400,1050),'#fafafa');d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=19)
    d.text((25,18),'Manufacturing study | CAD comparison | not a released print project',font=font,fill='#193247')
    d.text((25,58),'BLUE: keep PLA    ORANGE: removable PLA core    CREAM: removable Support For PLA',font=small,fill='#193247')
    sections=[('1. Exterior release paddle: underside', [141.8,27.8,2.8],[144.5,33.3,6.3],[1,-.6,-.75],
               'Before: flat overhang needs automatic support','After: 45-degree underside; no auto support in slicing'),
              ('2. Fixed-end removable grips',[6.35,13.9,.1],[13.2,23,6.8],[1,-.55,.8],
               'Before: feet bond to tray through 3 extra interfaces','After: rising grips; feet and those interfaces removed')]
    for j,(title,lo,hi,cam,left,right) in enumerate(sections):
        y=105+j*445;d.text((25,y),title,font=font,fill='#193247')
        crop=g.v.box(np.array(hi)-lo,lo)
        for x,q in ((20,old),(720,new)):
            items=colored(q,crop)
            if j==0:items=items[:1]
            im.paste(render(items,cam,(660,340)),(x,y+40))
        d.text((25,y+389),left,font=small,fill='#193247');d.text((725,y+389),right,font=small,fill='#193247')
    d.text((25,1006),'Geometry + slicer evidence only. Grip strength, surface finish and removal force await physical testing.',font=small,fill='#804327')
    im.save(g.OUT/'comparison.png')

if __name__=='__main__':main()
