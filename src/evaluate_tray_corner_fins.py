"""Assess removal of obsolete 0.4 mm post-relief fins.
Not a released printing project. Keep production snapshots unchanged.
"""
import sys,json
from pathlib import Path
import numpy as np
import build_v4_3 as d
v=d.v

def modify(p,fixed,leaves):
    p,fixed,leaves=d.modify(p,fixed,leaves)
    for name in ('tray-middle-3','tray-top-3'):
        # Obsolete 0.4 mm web between old and new post-clearance cuts.
        # Include the 0.6 mm floor remnant so no fragile horizontal whisker
        # remains after removing the upright web. Stop at the main end rail.
        strip=v.box((4.661,.402,4.61),(1.89,94.899,-.1))
        cut=strip+strip.mirror((1,0,0)).translate((147,0,0))
        fixed[name]-=cut
        remnant=v.box((4.65,.398,4.6),(1.9,94.901,-.1))
        remnant+=remnant.mirror((1,0,0)).translate((147,0,0))
        assert (fixed[name]^remnant).volume()<1e-7,'floor remnant survives'
        p[name]=fixed[name]
        for _,s in leaves[name]:p[name]+=s
        p[name]=p[name].set_tolerance(.001).simplify(.001)
    return p,fixed,leaves

def main():
    out=d.base.ROOT/'build/tray-guide-assessment';out.mkdir(exist_ok=True)
    d.configure();old,_,_=d.base.parts()
    d.base.PART_MODIFIER=modify
    new,fixed,leaves=d.base.parts()
    for name in old:
        if not name.startswith('tray'):
            assert (new[name]-old[name]).volume()<1e-7 and (old[name]-new[name]).volume()<1e-7
    checks=d.base.verify(new,fixed,leaves,lid_up_probe=.55)
    rows={}
    for name in ('tray-middle-3','tray-top-3'):
        rows[name]={'added_mm3':(new[name]-old[name]).volume(),'removed_mm3':(old[name]-new[name]).volume()}
        v.meshof(new[name]).export(out/(name+'.stl'))
    from PIL import Image,ImageDraw,ImageFont
    from support_removal_guide import render
    crop=v.box((12.,19.,7.),(0,83.,0))
    before=old['tray-middle-3']^crop;after=new['tray-middle-3']^crop
    removed=before-after
    im=Image.new('RGB',(1250,650),'#fafafa');pen=ImageDraw.Draw(im);font=ImageFont.load_default(size=23)
    pen.text((20,15),'Tray corner study | orange = obsolete 0.4 mm fin to remove',font=font,fill='#183247')
    for x,items,label in [(10,[(v.meshof(after),(72,150,180)),(v.meshof(removed),(235,140,45))],'V4.3: residual fin between post cutouts'),(635,[(v.meshof(after),(72,150,180))],'Candidate: remove fin, retain locating faces')]:
        im.paste(render(items,[1,1,1.3],(600,480)),(x,70))
        pen.text((x+10,565),label,font=ImageFont.load_default(size=19),fill='#183247')
    pen.text((20,610),'One at each short end near Y95; two per tray. Geometry study, physical testing pending.',font=ImageFont.load_default(size=19),fill='#183247')
    im.save(out/'corner-fin-comparison.png')
    result={'status':'geometry-only candidate, not a printable release','changes':rows,'checks':checks,
            'bottom_remnant_removed':True,
            'old_relief_fins_mm':.4,'retain_existing_PCB_guides':True,'body_and_lid_unchanged':True,
            'physical_strength_verified':False}
    (out/'assessment.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
