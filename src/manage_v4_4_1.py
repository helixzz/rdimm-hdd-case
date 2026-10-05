"""Reproducible complete version-marked release pipeline."""
import argparse
from pathlib import Path
from build_v4_4_1 import VERSION,parts,ROOT

def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','audit','preview','package'])
    p.add_argument('--bambu',type=Path);p.add_argument('--profiles',type=Path);a=p.parse_args()
    if a.stage=='prepare':
        if not a.bambu or not a.profiles:p.error('prepare requires --bambu and --profiles')
        import prepare_v4_4 as m;m.main(a.bambu,a.profiles,VERSION,parts)
    elif a.stage=='audit':
        import audit_v4_4_details as m;m.main(VERSION)
        import audit_version_marks as labels;labels.main()
    elif a.stage=='preview':
        import preview_v4_4 as m;m.main(VERSION,parts)
        import preview_version_marks as labels;labels.main()
    else:
        import package_v4_4 as m;m.main(VERSION)

if __name__=='__main__':main()
