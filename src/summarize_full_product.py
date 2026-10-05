"""Publish full-product research measurements, without local presets or toolpaths."""
import json,shutil
from evaluate_full_product import ROOT,OUT

def main():
    dest=ROOT/'docs/reports/full-product-study';dest.mkdir(parents=True,exist_ok=True)
    summaries=[]
    for path in sorted(OUT.glob('*-slicing.json')):
        data=json.loads(path.read_text());rows=data['results'] if isinstance(data,dict) else data
        products=data.get('products',1) if isinstance(data,dict) else 1
        seconds=sum(r['seconds'] for r in rows);grams={}
        for row in rows:
            assert not row['warnings'],(path.name,row['warnings'])
            for f in row['filaments']:
                k=f['filament_id'];grams[k]=grams.get(k,0)+f['total_used_g']
        summaries.append(dict(mode=path.stem.removesuffix('-slicing'),products=products,plates=len(rows),
            seconds=seconds,seconds_per_product=seconds/products,
            changes=sum(r['changes'] for r in rows),grams=grams,grams_per_product={k:v/products for k,v in grams.items()}))
        shutil.copyfile(path,dest/path.name)
    for path in OUT.glob('*-geometry.json'):shutil.copyfile(path,dest/path.name)
    audit=json.loads((OUT/'audit-summary.json').read_text());assert all(r['passed'] for r in audit)
    shutil.copyfile(OUT/'audit-summary.json',dest/'audit-summary.json')
    details=[]
    for row in audit:
        path=OUT/row['mode']/row['plate']/'whole-plate-audit.json'
        details.append(dict(mode=row['mode'],plate=row['plate'],audit=json.loads(path.read_text())))
    (dest/'toolpath-audits.json').write_text(json.dumps(details,indent=2))
    (dest/'summary.json').write_text(json.dumps(summaries,indent=2))
    shutil.copyfile(OUT/'batch-layout.png',dest/'batch-layout.png')
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
