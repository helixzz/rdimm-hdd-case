"""CAD-derived plate, support-removal and split-keeper assembly illustrations."""
import json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from build_trial_v4_4_rc5 import ROOT,VERSION,parts,v,split,study
from support_removal_guide import render

BLUE=(72,139,180);ORANGE=(235,127,47);CREAM=(224,196,130);GREEN=(67,155,116)
def colored(q,crop=None,shift=False):
    items=[]
    for shapes,color in [([q['model']],GREEN if q['kind']=='keeper' else BLUE),(q['cores'],ORANGE),(q['interfaces'],CREAM)]:
        for s in shapes:
            s=s if crop is None else s^crop
            if s.volume()<1e-6:continue
            if shift:s=s.translate(q['translation'])
            items.append((v.meshof(s),color))
    return items

def main():
    qs,_=parts();lookup={q['name']:q for q in qs};out=ROOT/f'models/v{VERSION}';folder=ROOT/f'build/v{VERSION}-projects'
    report=json.loads((folder/'slicing-report.json').read_text());audit=json.loads((folder/'toolpath-audit.json').read_text())
    font=ImageFont.load_default(size=25);small=ImageFont.load_default(size=19)
    im=Image.new('RGB',(1400,1500),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,16),'V4.4 RC5 | ONE PLATE | A integral / B separate fixed keeper',font=font,fill='#193247')
    d.text((25,57),'BLUE + GREEN stay | ORANGE handle + CREAM comb come out together',font=small,fill='#804327')
    items=[(v.meshof(v.box((256,256,.1),(0,0,-.2))),(239,242,245))]
    for q in qs:items+=colored(q,shift=True)
    a,b=np.array(audit['tower_xy_bounds']);items.append((v.meshof(v.box([*(b-a),.1],[*a,0])),(135,139,147)))
    im.paste(render(items,[0,-.00001,1],(1280,1280)),(60,100))
    for q in qs:
        bb=np.array(q['model'].bounding_box()).reshape(2,3)+q['translation'];x=bb[:,0].mean();y=bb[0,1]-3
        d.text((77.5+x*1245/256,117.5+(256-y)*1245/256),q['name'],font=font,fill='#193247',anchor='mt')
    d.text((25,1380),'A and B each hold ONE DIMM. B-KEEPER is a permanent part: do not discard it.',font=small,fill='#193247')
    d.text((25,1415),'H32 unchanged | P1 actual shell crop: corrected empty mounting holes | Grey: prime tower',font=small,fill='#193247')
    seconds=round(report['estimated_seconds']);grams=sum(f['total_used_g'] for f in report['filaments'])
    d.text((25,1450),f'P2S / 0.4 / 0.20 | {seconds//3600}h {seconds%3600//60:02}m {seconds%60:02}s | {grams:.2f} g | {report["filament_changes"]} changes',font=small,fill='#193247');im.save(out/'plate-guide.png')
    im=Image.new('RGB',(1400,1420),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,15),'V4.4 RC5 | Sparse supports | CAD reference, not a printed result',font=font,fill='#193247')
    d.text((25,55),'Hold BLUE structure. Pull ORANGE + CREAM toward the empty DIMM slot / C label.',font=small,fill='#804327')
    for i,(title,q,lo,hi,cam,note) in enumerate([
        ('A fixed end / ONE connected comb',lookup['A'],[6.2,13.8,0],[11.5,23.2,7],[1,-.6,1.1],'Fingers replace broad contact sheets. Pull +X; do not lever on the blue roof.'),
        ('A + B moving end',lookup['A'],[135.5,27.2,0],[145.1,34,7],[-1,-.5,1.1],'Pull -X into the slot. BLUE spring and exterior gusset stay.'),
        ('C1 + C3 / end contacts retained',lookup['C1'],None,None,[1,-1,1.1],'Pull toward C label. Check both end contacts for residue; no clean-release guarantee.')]):
        y=100+i*420;d.text((25,y),title,font=font,fill='#193247');crop=v.box(np.array(hi)-lo,lo) if lo else None
        keep=q['model'] if crop is None else q['model']^crop
        im.paste(render(colored(q,crop),cam,(650,300)),(20,y+38));im.paste(render([(v.meshof(keep),BLUE)],cam,(650,300)),(730,y+38))
        d.text((25,y+350),'Before removal',font=small,fill='#804327');d.text((735,y+350),'Clean reference',font=small,fill='#193247')
        d.text((25,y+383),note,font=small,fill='#193247')
    d.text((25,1380),'Stop if the handle cracks; record any film/rib residue before using a tool.',font=small,fill='#804327');im.save(out/'support-removal.png')
    q=study.g.specimens('combined')[0];source=q['model']+v.box((4.4,14.,4.4),(1.9,34.9,0))
    body,rail,leaf,rec=split.split(source,[2.5],end=45.)
    crop=v.box((10,37,8),(0,12,0));body=body^crop
    im=Image.new('RGB',(1500,1350),'#fafafa');d=ImageDraw.Draw(im)
    d.text((25,18),'B | Fixed end without support | Flip B-KEEPER over before assembly',font=font,fill='#193247')
    cases=[('1  Align LARGE holes with the two posts',rail.translate((0,3.8,5)),[1,-.5,1.1]),
           ('2  Lower; lift the narrow side latch slightly',rail.translate((0,3.8,0)),[1,-.5,1.1]),
           ('3  Slide 3.8 mm so POSTS enter the SMALL ends',rail,[1,-.5,1.1]),
           ('4  Release latch; check lift + reverse-slide stops',rail,[-1,.3,1.1])]
    for i,(title,s,cam) in enumerate(cases):
        x=20+(i%2)*740;y=85+(i//2)*575;d.text((x,y),title,font=small,fill='#193247')
        im.paste(render([(v.meshof(body),BLUE),(v.meshof(s),GREEN)],cam,(700,480)),(x,y+40))
    d.text((25,1250),'GREEN keeper stays installed. Its side latch blocks sliding; the two posts retain upward loads.',font=small,fill='#193247')
    d.text((25,1285),'Fit DIMM only after locking. Use the moving clip at the other end for normal DIMM removal.',font=small,fill='#193247')
    d.text((25,1320),'One shortened keeper in this coupon; full-product study uses one keeper per tray / integrated base.',font=small,fill='#804327');im.save(out/'B-assembly.png')
    print(out,flush=True)

if __name__=='__main__':main()
