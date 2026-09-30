"""Audit final combined plate: support interfaces, open holes and removed fins."""
import json,hashlib
import numpy as np
from build_combined_trial_v4_4_rc2 import ROOT,VERSION
from audit_support_trial_v4_4 import surface_gap
from audit_v3_2_toolpaths import parse,select,grid,footprint

def main():
    folder=ROOT/f'build/v{VERSION}-projects';path=folder/'0-combined/plate_1.gcode';segs=parse(path)
    records=json.loads((ROOT/f'models/v{VERSION}/verification.json').read_text())['specimens'];rows=[]
    for r in records:
        s=segs.copy();t=r['translation'];s[:,[0,2]]-=t[0];s[:,[1,3]]-=t[1];s[:,4]-=t[2]
        name=r['name'];kind=r['kind'];item={'name':name,'kind':kind,'checks':[]}
        def gap(rect,split,label):
            value=surface_gap(s,rect,split);assert value>=.19,(name,label,value)
            item['checks'].append({'region':label,'gap_mm':round(value,4)})
        if kind=='dimm':
            for label,rect in [('fixed-land',[6.8,15,7.25,15.5]),('fixed-middle',[6.8,16,7.25,17.7]),('tooth-land',[139.85,28.55,140.2,29.05]),('tooth-middle',[139.85,29.7,140.2,31.3])]:
                for split in (3.1,4.5):gap(rect,split,label+' '+str(split))
            for label,rect in [('left-foot',[8.7,15.2,12.5,17.8]),('right-foot',[134.2,28.7,138,32.2])]:gap(rect,.7,label)
            rect=[143.25,28.8,144.1,32.2];ss=select(s,rect)
            assert np.any((ss[:,7]==1)&(ss[:,4]>=5)&(ss[:,4]<=5.2)),(name,'missing paddle support')
            gap(rect,5.3,'automatic paddle support')
        elif kind=='capture':
            length=r['capture_length']
            for yy in (2.3,2+length-.9):
                for split in (3.1,4.7):gap([3.8,yy+.1,5.8,yy+.5],split,'runner '+str(yy)+' '+str(split))
            ss=select(s,[3.3,2.1,6.4,2+length-.1]);ss=ss[(ss[:,7]==1)&(ss[:,4]>3.01)&(ss[:,4]-ss[:,6]<4.79)]
            assert len(ss)==0,(name,'duplicate automatic support',len(ss))
            item['checks'].append({'duplicated_automatic_support':0})
            # Top-layer fill differs between long/short pads. Check an actual
            # connected bead path through adjacent layers, not solid infill.
            rect=[6.2,2+length/2-1.2,8.1,2+length/2+1.2]
            xx,yy=grid(rect);zs=np.arange(3.8,5.21,.2)
            voxels=np.zeros((len(zs),)+xx.shape,dtype=bool)
            for q in select(s,rect):
                if q[7]!=0:continue
                layer=int(np.argmin(abs(zs-q[4])))
                if abs(zs[layer]-q[4])<.01:voxels[layer]|=footprint(q,xx,yy)
            reached=np.zeros_like(voxels)
            reached[0]=voxels[0]&(xx<6.5)
            assert reached.any(),(name,'neck seed absent')
            while True:
                nxt=reached.copy()
                for axis in range(3):
                    a=[slice(None)]*3;b=a.copy();a[axis]=slice(1,None);b[axis]=slice(None,-1)
                    nxt[tuple(a)]|=reached[tuple(b)];nxt[tuple(b)]|=reached[tuple(a)]
                nxt&=voxels
                if np.array_equal(nxt,reached):break
                reached=nxt
            assert np.any(reached[-1]&(xx>7.2)),(name,'grip disconnected in nominal beads')
            item['checks'].append({'grip_neck_connected_nominal_beads':True,'checked_layer_tops_mm':zs.round(2).tolist(),'grid_pitch_mm':.025})
        elif kind=='mount':
            radius=r['diameter']/2
            for title,rect,lo,hi in [('bottom',[15-radius,3.175-radius,15+radius,3.175+radius],0,5.31),('side',[5-radius-.31,0,5+radius+.31,5.7],6.35-radius-.31,6.35+radius+.31)]:
                ss=select(s,rect);ss=ss[(ss[:,7]==1)&(ss[:,4]>lo)&(ss[:,4]-ss[:,6]<hi)]
                assert len(ss)==0,(name,title,'hole support remains',len(ss))
                item['checks'].append({'hole':title,'support_segments':0})
            ss=select(s,[14.5,2.7,15.5,3.7]);ss=ss[(ss[:,7]==0)&(ss[:,4]>4.9)&(ss[:,4]<6.)]
            assert len(ss)>0,(name,'missing bottom roof')
            item['checks'].append({'bottom_roof_lowest_nominal_bead_bottom_mm':float(np.min(ss[:,4]-ss[:,6]))})
        else:
            rect=[2.2,4.95,6.2,5.25];xx,yy=grid(rect);ss=select(s,rect);hits=[]
            for q in ss:
                if .21<q[4]<4.51 and footprint(q,xx,yy).any():hits.append(q.tolist())
            assert not hits,(name,'printed fin remnant',len(hits))
            item['checks'].append({'fin_and_floor_remnant_above_first_layer':False})
        rows.append(item)
    report={'version':VERSION,'gcode_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'specimens':rows,'limits':'Nominal bead audit, not physical support-release, bridging, screw torque, pin compatibility or strength verification. Fin path check excludes the first layer.'}
    (folder/'toolpath-audit.json').write_text(json.dumps(report,indent=2));print('Passed',len(rows),'specimens')
if __name__=='__main__':main()
