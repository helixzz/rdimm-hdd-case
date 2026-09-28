# Agent collaboration guide

## Project and source of truth
- This repository designs a printable RDIMM storage enclosure matching a traditional 3.5-inch HDD envelope and mounting positions.
- `src/build_case.py` is the current v2 source of truth; `models/v2/` contains its printable baseline. `src/build_v1.py` and `models/v1/` preserve v1. Read `docs/v2.zh-CN.md` for v2 printing/assembly and `docs/printing.zh-CN.md` for original dimension references.
- Work from the latest main branch in a task branch. Read the current diff before editing; preserve other contributors' changes. Keep generated scratch output under ignored `build/`.

## Established design constraints
- Current outer envelope: 147 x 101.6 x 26 mm. Current capacity: 8, arranged 2+3+3. Units: mm.
- Reference module: 133.80 x 31.40 x 5.57 mm maximum envelope. This is a reference drawing, not verified exact Samsung M321RAJA0MB2-CCP geometry.
- The 2 mm component-free short PCB edges are an unverified assumption used by the clearance model. Do not silently turn this into a verified fact.
- HDD interfaces use 6-32 UNC. V2 provides two alternative bodies: all plastic pilots, or six side bores for PEM IUTB-632-150 inserts. Bottom holes remain plastic pilots (3.3 mm deep); lid pilots remain M2. Do not confuse nominal printed bore sizes with the manufacturer's required finished bore. Preserve the documented 3.0 mm installed screw penetration limit unless the geometry and documentation are revised together.
- Never rescale the entire design to adjust printing fit: mounting coordinates must remain intentional.
- Do not infer chassis clearance for a taller variant, physical fit from a mesh check, ESD properties from ordinary filament, or the mathematical maximum capacity from this layout.

- V2 base/pitch/lid are 4.0/6.8/1.6 mm. Nominal component gaps are 0.30 mm below and 0.33 mm above to the next tray. The lid has 0.2 mm total stack relief. Do not mix versions.
- Pull eyes and lid locators do not establish arbitrary-orientation PCB retention; there is no independent PCB latch. Insert pullout strength and ESD are also unverified.

## Build and validation
Use Python 3.12. Install `requirements.txt`, then run `python src/build_case.py` without `-O`. This exports nine STL files under `build/` and checks mesh, both assemblies, reference modules, 64 component-offset cases, maximum insert envelopes, coupon stacking, screw clearances and the assembled envelope. Inspect `build/verification.json` and the preview. There are no required global CAD applications or machine-specific cache paths.

For an intentional baseline update run `python src/build_case.py --output-dir models/v2`, review generated changes, and update source, artifacts, and documentation together. New incompatible variants should use a new model directory. Describe changes and validation in the PR; automated geometry checks do not replace slicing, printing, or fit testing.

## Provenance and publication
Retain dimension citations and distinguish assumptions from measured data. Do not add third-party PDFs, private workspace files, credentials, machine-specific paths, or user conversations. The project uses MIT for original contributions. Do not claim unperformed physical tests or certification.
