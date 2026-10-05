"""Complete v4.4 product, using the physically tested RC6 solid supports."""
import argparse,json
from pathlib import Path
import numpy as np
import study_solid_support_v4_4_rc6 as solid

ROOT=solid.ROOT; VERSION='4.4'; v=solid.v

def parts():
    return solid.product(5.0)

def build(out):
    out.mkdir(parents=True,exist_ok=True)
    plates,checks=parts();records=[];plate_records=[];changes={}
    solid.s.g.design.configure();previous,_,_=solid.base.parts()
    assert checks['connected_insert_count']==20
    for label,items in plates:
        folder=out/label
        original=solid.full.export(items,folder,VERSION+'-'+label)
        target=folder/f'rdimm-{VERSION}-plate-{label}.3mf'
        original.replace(target)
        path=folder/'verification.json';meta=json.loads(path.read_text())
        meta.update(version=VERSION,scope='Complete product plate; dedicated supports required',
                    physical_verified=False,physical_evidence='RC6 coupons: clean removal; fixed/C require tools')
        path.write_text(json.dumps(meta,indent=2))
        for q in items:
            local=q['model'].transform(np.array(q['inverse'])[:3,:])
            assert len(local.decompose())==1 and v.meshof(local).is_watertight
            changes[q['name']]=dict(added_mm3=(local-previous[q['name']]).volume(),removed_mm3=(previous[q['name']]-local).volume())
            if q['name'].startswith('lid'):assert max(changes[q['name']].values())<.001
            v.meshof(local).export(out/(q['name']+'.stl'))
        records.append(dict(plate=label,project=target.name,permanent_parts=[q['name'] for q in items],
                            dedicated_supports=sum(len(q['interfaces']) for q in items)))
        plate_records.append(dict(stem=f'rdimm-{VERSION}-plate-{label}',poses=[dict(part=q['name'],assembly_to_plate=np.linalg.inv(q['inverse']).tolist()) for q in items]))
    checks.update(version=VERSION,plates=records,plate_records=plate_records,changes_from_v4_3=changes,scope='Complete four-part eight-DIMM case',
                  support_baseline='RC6 solid 5.0 mm grip; no untested peel cuts',
                  physical_complete_set_verified=False,physical_impact_verified=False)
    (out/'verification.json').write_text(json.dumps(checks,indent=2));print('PASS v4.4 geometry',checks['checks'],flush=True)
    roots=json.loads((ROOT/'models/v4.3/tray-root-fix.json').read_text())
    roots.update(version=VERSION,inherited_from='4.3',scope='Unchanged root/tooth ROI definitions; fresh toolpath audit required')
    (out/'tray-root-fix.json').write_text(json.dumps(roots,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output-dir',type=Path,default=ROOT/'models/v4.4');build(p.parse_args().output_dir)
