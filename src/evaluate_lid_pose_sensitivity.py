"""Read-only CAD sensitivity study; does not export or change printable models."""
import argparse
import json
from pathlib import Path
import subprocess
import build_v4_1_rc3 as design

ROOT=Path(__file__).resolve().parents[1]


def run(out):
    design.previous.configure();old,fixed,_=design.base.parts()
    design.configure();new,_,_=design.base.parts()
    body=fixed['body-pin-clearance']
    results=[]
    for label,p in [('4.1-rc2',old),('4.1-rc3',new)]:
        for name,dx,dz in [('nominal',0,0),('x-only',.3,0),('z-only',0,.15),('combined',.3,.15)]:
            poses=[]
            for dy in (0,-2,-4,-6,-8):
                overlap=p['lid-slide-lift'].translate((dx,dy,dz))^body
                volume=overlap.volume()
                if name=='nominal':assert volume<.001
                poses.append({'y_slide_mm':dy,'intersection_mm3':volume,
                    'bounds_mm':list(overlap.bounding_box()) if volume>.001 else None})
            results.append({'lid':label,'case':name,'x_offset_mm':dx,'z_offset_mm':dz,'poses':poses})
    new_cases={r['case']:r for r in results if r['lid']=='4.1-rc3'}
    assert new_cases['x-only']['poses'][0]['intersection_mm3']<.001
    assert new_cases['z-only']['poses'][0]['intersection_mm3']<.001
    assert new_cases['combined']['poses'][0]['intersection_mm3']>.1
    report={'cad_source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'scope':'RC2 fixed body excludes flexible members, to isolate capture friction regions; not a complete released/loaded assembly test.',
        'offsets_are_measured':False,'physical_failure_proven':False,'new_printable_model_generated':False,
        'limits':'Exploratory rigid offsets are not a calibrated printer error model. Intersection volume is not force, friction, failure probability or load capacity.',
        'results':results}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf8')
    print('RC3 nominal and individual offsets clear at closure; combined offset intersects:',new_cases['combined']['poses'][0]['intersection_mm3'],'mm3')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/lid-pose-sensitivity.json')
    run(parser.parse_args().output)
