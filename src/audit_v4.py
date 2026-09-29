"""Inspect nominal Bambu extrusion beads at V4 support and flexure regions."""
import json
import hashlib
import numpy as np
from build_v4 import ROOT, v3, rc, SATA_Y
from audit_v3_2_toolpaths import parse,select,grid,footprint,side_gap,STEP,transformed_rect,check_math


def run(version='4.0-rc1',depth=6.,geometry_version=None):
    check_math()
    folder=ROOT/('build/v'+version+'-projects')
    records=json.loads((ROOT/('models/v'+(geometry_version or version))/'verification.json').read_text())['plate_records']
    reinforced=(geometry_version or version).startswith('4.1-')
    report={'version':version,'method':'Finite-width nominal G-code bead footprints; variable layer heights; 0.025 mm XY samples',
            'limits':'No thermal, sagging, bond, support removal, force or fatigue simulation','plates':[]}
    for label in ('1-pin-clearance','2-upper-trays'):
        path=folder/label/'plate_1.gcode';segs=parse(path)
        record=next(r for r in records if r['stem'].endswith('plate-'+label))
        rois=[];corridors=[]
        for pose in record['poses']:
            name=pose['part'];t=np.array(pose['assembly_to_plate'])
            if name.startswith('lid'):
                if reinforced:
                    for y,length in [(8.,6.),(95.6,4.2)]:
                        for x in (3.4,140.4):
                            rect=[x,y+.2,x+3.2,y+length-.2]
                            rois.append((name,f'flat tongue {x}/{y}',transformed_rect(rect,t),2.2))
                continue
            local=[];free=[]
            if name.startswith('body'):
                local += [('shell leaf',[49. if reinforced else 47.5,0,77,1.6],22.8 if reinforced else 23.),('SATA roof',[0,SATA_Y,depth,SATA_Y+47],6.2)]
                if reinforced:
                    for y,length in [(8.,6.),(95.6,4.2)]:
                        for x in (3.4,140.6):
                            local.append((f'flat capture {x}/{y}',[x,y+.2,x+3.,y+length-.2],24.))
                free += [('shell free end',[77.3,.1,77.7,1.5],23.,26.)]
                n=2;z=4.
            else:n=3;z=0.
            for i,sy in enumerate(v3.layout(n)[2]):
                y=rc.simple.clip_start(n,i,sy)
                local += [(f'fixed hood {i+1}',[6.3,sy+12,7.9,sy+20],4.6+z),
                          (f'tooth {i+1}',[139.4,y+(13.6 if reinforced else 14),142.,y+(18.4 if reinforced else 18)],4.6+z),
                          (f'paddle {i+1}',[143. if reinforced else 142.8,y+14,144.3,y+18],5.4+z)]
                if z:local += [(f'bottom beam foot {i+1}',[142.,y+1,142.8,y+13],4.)]
                free += [(f'beam slit {i+1}',[141.3,y+1,141.8,y+13],z,6.2+z)]
            for title,rect,zroof in local:
                rois.append((name,title,transformed_rect(rect,t),zroof+t[2,3]))
            for title,rect,zlo,zhi in free:
                corridors.append((name,title,transformed_rect(rect,t),zlo+t[2,3],zhi+t[2,3]))
        supports=[];channels=[]
        for name,title,rect,roof in rois:
            near=select(segs,rect);xx,yy=grid(rect)
            top=np.full(xx.shape,-np.inf);bottom=np.full(xx.shape,np.inf)
            for s in near[(near[:,7]==1)&(near[:,4]>=roof-.5)&(near[:,4]<roof-.05)]:
                hit=footprint(s,xx,yy);top[hit]=np.maximum(top[hit],s[4])
            for s in near[(near[:,7]==0)&(near[:,4]-near[:,6]>=roof-.05)&(near[:,4]-near[:,6]<roof+.4)]:
                hit=footprint(s,xx,yy);bottom[hit]=np.minimum(bottom[hit],s[4]-s[6])
            overlap=np.isfinite(top)&np.isfinite(bottom)
            assert overlap.any(),('missing support overlap',name,title)
            gap=float((bottom[overlap]-top[overlap]).min())
            assert gap>=.19,('Z contact',name,title,gap)
            side=side_gap(segs,rect,max(0,roof-2),roof+.6)
            assert side is None or side>.1,('XY contact',name,title,side)
            supports.append({'part':name,'region':title,'rect':rect,'roof_z':roof,'nominal_z_gap_mm':round(gap,4),
                             'nominal_xy_gap_mm':side,'support_overlap_mm2':round(float(overlap.sum()*STEP**2),3)})
        for name,title,rect,lo,hi in corridors:
            near=select(segs,rect);near=near[(near[:,4]>lo+.01)&(near[:,4]-near[:,6]<hi-.01)]
            xx,yy=grid(rect)
            hits=[s for s in near if footprint(s,xx,yy).any()]
            assert not hits,('closed free corridor',name,title,len(hits))
            channels.append({'part':name,'region':title,'intruding_extrusions':0})
        report['plates'].append({'plate':label,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                                 'project_sha256':hashlib.sha256(next((folder/label).glob('*P2S*.3mf')).read_bytes()).hexdigest(),
                                 'support_regions':supports,'free_corridors':channels})
        print(label,len(supports),'support gaps;',len(channels),'clear corridors',flush=True)
    (folder/'finite-width-audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default='4.0-rc1')
    parser.add_argument('--depth',type=float,default=6.)
    parser.add_argument('--geometry-version')
    args=parser.parse_args();run(args.version,args.depth,args.geometry_version)
