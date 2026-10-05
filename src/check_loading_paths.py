"""Reproduce reported RC1 tray loading failures; assess bottom-integration space.

This is a diagnosis of existing geometry, not a printable v4 design or a
proof that every possible rotated/translated loading path is impossible.
"""
from pathlib import Path
import json
import numpy as np
import build_v3_2 as rc1

ROOT=Path(__file__).resolve().parents[1]
v3=rc1.v3


def run():
    body=rc1.old_part('body-pin-clearance')
    revised,_=rc1.revised_body('body-pin-clearance')
    open_body=body-v3.rail()-v3.opposite(v3.rail())
    configs=[('test-tray-1',1,False,'1',4.),('tray-bottom-2',2,True,'1',4.),
             ('tray-middle-3',3,False,'2',10.8),('tray-top-3',3,False,'3',17.6)]
    report={'scope':'Rigid straight-down loading and nominal seated poses only; no physical validation',
            'upper_opening_x_mm':140.6,'trays':[]}
    for name,n,bottom,tier,seat in configs:
        tray,_,leaves=rc1.revised_tray(name,n,bottom,tier)
        samples=[]
        open_path_max=0.
        for z in np.linspace(28.,seat,121):
            volume=(tray.translate((0,0,float(z)))^body).volume()
            if name!='test-tray-1':
                open_path_max=max(open_path_max,(tray.translate((0,0,float(z)))^open_body).volume())
            if volume>.0001: samples.append({'tray_bottom_z':round(float(z),4),'intersection_mm3':round(volume,5)})
        assert samples,('Failure no longer reproduced',name)
        seated=(tray.translate((0,0,seat))^body).volume()
        if bottom or n==3: assert seated<.0001,('Unexpected seated collision',name,seated)
        else: assert seated>1,('Expected coupon lacks bottom recess',seated)
        item={'part':name,'tray_length_mm':round(v3.meshof(tray).extents[0],4),
              'tested_base_z':seat,'seated_intersection_mm3':round(seated,5),
              'straight_loading_blocked':True,'blocked_sample_count':len(samples),
              'highest_blocked_z':samples[0]['tray_bottom_z'],
              'max_path_intersection_mm3':max(s['intersection_mm3'] for s in samples),
              'rc1_body_collision_at_same_highest_pose_mm3':round((tray.translate((0,0,samples[0]['tray_bottom_z']))^revised).volume(),5)}
        if name!='test-tray-1':
            item['hypothetical_rails_removed_max_path_intersection_mm3']=round(open_path_max,5)
            assert open_path_max<.0001
        if name=='test-tray-1':
            item['pose_scope']='Hypothetical placement at bottom-tray height; this coupon is not an assembly tray'
            item['seated_collision_bounds']=v3.meshof(tray.translate((0,0,seat))^body).bounds.tolist()
            item['sata_roof_region_intersection_mm3']=round((tray.translate((0,0,seat))^body^v3.box((6.8,47.,3.),(0,11,4))).volume(),5)
        if bottom:
            item['existing_outward_release_body_collisions_mm3']=[round((rc1.simple.bend(leaf,y,1.5).translate((0,0,seat))^body).volume(),5) for y,leaf in leaves]
            assert any(v>0 for v in item['existing_outward_release_body_collisions_mm3'])
        report['trays'].append(item)
    report['bare_bottom_reference_modules']=[]
    for sy in v3.layout(2)[2]:
        maximum=0.
        for pcb_z in np.linspace(30.,7.,116):
            ram=rc1.simple.module(133.8,31.4,1.37,6.6,sy+.2,float(pcb_z))
            maximum=max(maximum,(ram^body).volume())
        assert maximum<.0001
        report['bare_bottom_reference_modules'].append({'pcb_y':sy+.2,'pcb_z_seated':7.,
                                                       'maximum_straight_loading_intersection_mm3':round(maximum,6)})
    report['integration_constraints']={
        'capacity_target':8,'layout':'2 fixed bottom seats + 3 middle tray + 3 top tray',
        'part_count_before':5,'part_count_concept':4,'plate_count_and_print_time':'Not established; requires full new model and slicing',
        'connector_body_roof_z_mm':7.,'current_bottom_pcb_z_mm':7.,
        'nominal_chip_start_x_mm':8.6,'connector_body_inner_x_mm':6.8,
        'existing_latch_reuse':'Not drop-in: outward release collides with body and its beam foot would join the body floor',
        'top_opening':'Upper trays still blocked; removing the bottom tray does not fix the lid rails',
        'claim_limit':'Bare modules are tested against body only. No integrated keepers, handling clearance or finished v4 are validated.'}
    out=ROOT/'build/loading-path-diagnosis';out.mkdir(parents=True,exist_ok=True)
    (out/'report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':run()
