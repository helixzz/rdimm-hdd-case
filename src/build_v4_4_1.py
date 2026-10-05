"""Version-marked complete product. Historical v4.4 geometry stays immutable."""
import argparse,json
from pathlib import Path
import numpy as np
import build_v4_4 as baseline
from operation_marks import GLYPHS,stroke

ROOT=baseline.ROOT;VERSION='4.4.1';v=baseline.v;solid=baseline.solid
DEPTH=.2;WIDTH=.6

def text_shape(value):
    glyphs=dict(GLYPHS)
    glyphs.update({'0':GLYPHS['O'],'4':[[(0,3),(0,1.2),(2,1.2)],[(1.6,3),(1.6,0)]],
                  '5':GLYPHS['S'],'6':[[(2,3),(.5,3),(0,2.3),(0,.4),(.4,0),(1.6,0),(2,.4),(2,1.3),(1.6,1.7),(0,1.7)]],
                  '7':[[(0,3),(2,3),(.5,0)]],'8': [[(.4,1.5),(0,2),(0,2.6),(.4,3),(1.6,3),(2,2.6),(2,2),(1.6,1.5),(.4,1.5),(0,1),(0,.4),(.4,0),(1.6,0),(2,.4),(2,1),(1.6,1.5)]],
                  '9':[[(2,1.3),(.4,1.3),(0,1.7),(0,2.6),(.4,3),(1.6,3),(2,2.6),(2,.4),(1.6,0),(0,0)]],
                  '.':[[(.8,0)]],'-':[[(.2,1.5),(1.8,1.5)]],
                  'C':[[(2,3),(.4,3),(0,2.6),(0,.4),(.4,0),(2,0)]]})
    shape=v.m.CrossSection()
    for i,ch in enumerate(value):
        if ch!=' ':
            for path in glyphs[ch]:shape+=stroke(path,WIDTH).translate((3.1*i,0))
    return shape

def marks(name):
    if name.startswith('body'):
        return [('V'+VERSION+' BASE',text_shape('V'+VERSION+' BASE'),
                 [[1,0,0,50],[0,-1,0,40],[0,0,-1,DEPTH]],'underside',2.)]
    if name.startswith('lid'):
        return [('V'+VERSION+' LID',text_shape('V'+VERSION+' LID'),
                 [[1,0,0,50],[0,1,0,80],[0,0,1,26-DEPTH]],'exterior top',1.)]
    code='MID' if 'middle' in name else 'TOP'
    return [(label,text_shape(label).rotate(90),[[1,0,0,5.6],[0,1,0,y],[0,0,1,6.8-DEPTH]],'thick end rail',1.)
            for label,y in [('V'+VERSION,20),(code,68)]]

def parts():
    plates,checks=baseline.parts();records=[]
    for _,items in plates:
        for q in items:
            inv=np.array(q['inverse']);before=q['model'].transform(inv[:3,:]);after=before
            for label,shape,transform,surface,remaining in marks(q['name']):
                cut=shape.extrude(DEPTH+.1).transform(transform)
                removed=(before^cut).volume();expected=shape.area()*DEPTH
                assert abs(removed-expected)<.001,(q['name'],label,'not entirely on solid face',removed,expected)
                # Probe at least this much permanent material directly behind every stroke.
                t=np.array(transform,dtype=float);t[:,3]-=t[:,2]*remaining
                probe=shape.extrude(remaining).transform(t)
                assert (probe-before).volume()<.001,(q['name'],label,'insufficient backing')
                after-=cut
                records.append(dict(part=q['name'],text=label,surface=surface,depth_mm=DEPTH,
                                    stroke_width_mm=WIDTH,minimum_backing_mm=remaining,transform=transform,
                                    removed_mm3=removed))
            assert (after-before).volume()<.001 and len(after.decompose())==1 and v.meshof(after).is_watertight
            q['model']=after.transform(np.linalg.inv(inv)[:3,:])
    assert len({r['part'] for r in records})==4
    checks['physical_version_marks']=records
    return plates,checks

def build(out):
    out.mkdir(parents=True,exist_ok=True);plates,checks=parts();records=[];poses=[]
    for label,items in plates:
        folder=out/label;original=solid.full.export(items,folder,VERSION+'-'+label)
        target=folder/f'rdimm-{VERSION}-plate-{label}.3mf';original.replace(target)
        meta=json.loads((folder/'verification.json').read_text());meta.update(version=VERSION,physical_verified=False)
        (folder/'verification.json').write_text(json.dumps(meta,indent=2))
        for q in items:v.meshof(q['model'].transform(np.array(q['inverse'])[:3,:])).export(out/(q['name']+'.stl'))
        records.append(dict(plate=label,project=target.name,permanent_parts=[q['name'] for q in items],dedicated_supports=sum(len(q['interfaces']) for q in items)))
        poses.append(dict(stem=f'rdimm-{VERSION}-plate-{label}',poses=[dict(part=q['name'],assembly_to_plate=np.linalg.inv(q['inverse']).tolist()) for q in items]))
    checks.update(version=VERSION,plates=records,plate_records=poses,baseline='4.4; only recessed identification added',
                  physical_complete_set_verified=False,physical_impact_verified=False)
    (out/'verification.json').write_text(json.dumps(checks,indent=2))
    roots=json.loads((ROOT/'models/v4.4/tray-root-fix.json').read_text());roots.update(version=VERSION)
    (out/'tray-root-fix.json').write_text(json.dumps(roots,indent=2))
    print('PASS',VERSION,'all four permanent parts marked',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/f'models/v{VERSION}');build(p.parse_args().output_dir)
