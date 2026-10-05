"""Source-derived X60 section: the old high ridge and new floor-grown fillet."""
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import build_v4_2 as d


def main():
    d.previous.configure();old,_,_=d.base.parts()
    d.configure();new,_,_=d.base.parts()
    roi=d.v.box((.2,9.,12.),(59.9,0,0))
    # Regression: the old high inward ledge must be absent, floor fillet present.
    ridge=d.v.box((.1,.2,.2),(60,3.7,10.1))
    foot=d.v.box((.1,.2,.2),(60,5.5,4.1))
    assert (ridge^old['body-pin-clearance']).volume()>.003
    assert (ridge^new['body-pin-clearance']).volume()<1e-7
    assert (foot-new['body-pin-clearance']).volume()<1e-7
    im=Image.new('RGB',(1300,850),'#fafafa');pen=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=23);small=ImageFont.load_default(size=18)
    pen.text((20,20),'V4.2 | actual CAD section at X = 60 mm | near long wall',font=font,fill='#193247')
    for i,(title,part) in enumerate([('OLD: R2 floor + separate high ridge',old),('NEW: continuous concave R6 from floor',new)]):
        ox=55+i*650;oy=710;s=43
        def xy(y,z):return (ox+y*s,oy-z*s)
        pen.text((20+i*650,75),title,font=small,fill='#193247')
        section=(part['body-pin-clearance']^roi).rotate((0,-90,0)).slice(60)
        for poly in section.to_polygons():
            pen.polygon([xy(y,-x) for x,y in poly],fill='#4896b4')
        pen.line([xy(0,10.8),xy(10,10.8)],fill='#cf8732',width=2)
        pen.text(xy(1,11.5),'First tray bottom Z10.8',font=small,fill='#805024')
        pen.text(xy(2,2),'Floor top Z4',font=small,fill='white')
        if i:
            pen.text(xy(3,7),'R6',font=font,fill='#193247')
            pen.text(xy(2,10),'Top Z10',font=small,fill='#193247')
    pen.text((20,765),'0.8 mm vertical clearance to first tray; full module/loading paths checked separately.',font=small,fill='#193247')
    pen.text((20,800),'Mounting bores preserved. Section does not predict surface finish or impact strength.',font=small,fill='#804327')
    out=d.base.ROOT/'models/v4.2';im.save(out/'floor-transition-preview.png')
    (d.base.ROOT/'docs/reports/v4.2-floor-section.json').write_text(json.dumps({
        'section_x_mm':60,'old_ridge_reproduced':True,'new_ridge_absent':True,
        'floor_foot_present':True,'floor_z_mm':4,'fillet_top_z_mm':10,
        'tray_bottom_z_mm':10.8,'nominal_vertical_clearance_mm':.8,
        'method':'Actual CAD section and positive/negative local volume probes; full assembly checked by build_v4_2.',
        'physical_finish_verified':False},indent=2))


if __name__=='__main__':main()
