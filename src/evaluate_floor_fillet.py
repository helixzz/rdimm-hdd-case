"""Evaluate floor fillets against the actual RC3 assembly and mounting voids."""
import json
from pathlib import Path
import build_v4_rc3 as rc3
from build_v4_rc3 import base


from floor_fillet import fillets, mount_voids


def evaluate(out):
    rc3.configure()
    p,f,l=base.parts();rows=[]
    for radius in (1.,1.5,2.,3.):
        raw=fillets(radius,True)
        windows=base.m.Manifold()
        for y,_ in l['body-pin-clearance']:windows+=base.v3.box((5.9,19.,24.),(141.1,y,2.2))
        row={'radius_mm':radius,'top_z_mm':4+radius,'upper_tray_min_z_mm':10.8,
             'naive_full_ring_mount_void_fill_mm3':round((raw^mount_voids(True)).volume(),5),
             'naive_full_ring_release_window_fill_mm3':round((raw^windows).volume(),5)}
        candidate={k:v for k,v in p.items()};fixed={k:v for k,v in f.items()}
        for name in ('body-pin-clearance','body-thread-pilot'):
            extra=fillets(radius)-mount_voids(name.endswith('clearance'))
            candidate[name]+=extra;fixed[name]+=extra
        try:
            checks=base.verify(candidate,fixed,l)
            row['long_walls_preserving_holes']='pass';row['checks']=checks
        except AssertionError as e:
            row['long_walls_preserving_holes']='fail';row['reason']=str(e)
        added=candidate['body-pin-clearance']-p['body-pin-clearance']
        row['added_volume_mm3']=round(added.volume(),3)
        row['nominal_pla_mass_g_at_1_24']=round(added.volume()*.00124,3)
        rows.append(row)
    out.mkdir(parents=True,exist_ok=True)
    result={'baseline':'4.0-rc3','floor_z_mm':4.,'bottom_pcb_min_z_mm':7.,
            'reference_bottom_component_min_z_mm':4.9,'rows':rows,
            'limits':'Geometry and sampled paths only; no thermal or surface-finish prediction. PLA volume estimate is not sliced mass.'}
    (out/'floor-fillet-evaluation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':evaluate(base.ROOT/'build/floor-fillet-evaluation')
