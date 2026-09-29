# Agent collaboration guide

## Project and source of truth
- This repository designs a printable RDIMM storage enclosure matching a traditional 3.5-inch HDD envelope and mounting positions.
- `src/build_case.py` is the current v2 source of truth; `models/v2/` contains its printable baseline. `src/build_v1.py` and `models/v1/` preserve v1. Read `docs/v2.zh-CN.md` for v2 printing/assembly and `docs/printing.zh-CN.md` for original dimension references.
- Work from the latest main branch in a task branch. Read the current diff before editing; preserve other contributors' changes. Keep generated scratch output under ignored `build/`.
- User has physically printed v2 and reported carrying rattle. `src/build_retention.py` reads the unchanged v2 STL baseline and generates the experimental v2-R retrofit in `models/v2-retention/`; see `docs/retention.zh-CN.md`. Do not silently alter a previously printed v2 part to make the retrofit fit.
- Latest independent prototype is v3: `src/build_v3.py`, `models/v3/`, `docs/v3.zh-CN.md`. It reads v2-R meshes but changes the complete set. Daily use must require NO internal screws/tools: three keyed retainer frames are captured by the CLOSED sliding cover. Open trays are not inversion-safe cartridges. Two external lid reinforcement screws are optional only. Do not reintroduce the abandoned screwed interior.
- V3 must stay within 147 x 101.6 x 26 mm. Side/bottom hole depths are 5.7/5.3 mm with 5.0 mm occupied-probe checks; 3.6 mm pin-clearance and 2.7 mm thread-pilot bodies are alternatives, not interchangeable fastening methods. V3 does not include the old PEM insert variant.
- User confirmed a fixed backplane receptacle must be cleared. V3's X=0..6, Y=11..58, Z=0..6.2 recess is a trial envelope informed by SFF-8323, NOT a verified universal SATA cavity. Require empty gauge fit evidence before claiming the target backplane accepts it. All v3 physical checks remain pending.

## Established design constraints
- Current outer envelope: 147 x 101.6 x 26 mm. Current capacity: 8, arranged 2+3+3. Units: mm.
- Reference module: 133.80 x 31.40 x 5.57 mm maximum envelope. This is a reference drawing, not verified exact Samsung M321RAJA0MB2-CCP geometry.
- The 2 mm component-free short PCB edges are an unverified assumption used by the clearance model. Do not silently turn this into a verified fact.
- HDD interfaces use 6-32 UNC. V2 provides two alternative bodies: all plastic pilots, or six side bores for PEM IUTB-632-150 inserts. Bottom holes remain plastic pilots (3.3 mm deep); lid pilots remain M2. Do not confuse nominal printed bore sizes with the manufacturer's required finished bore. Preserve the documented 3.0 mm installed screw penetration limit unless the geometry and documentation are revised together.
- Never rescale the entire design to adjust printing fit: mounting coordinates must remain intentional.
- Do not infer chassis clearance for a taller variant, physical fit from a mesh check, ESD properties from ordinary filament, or the mathematical maximum capacity from this layout.

- V2 base/pitch/lid are 4.0/6.8/1.6 mm. Nominal component gaps are 0.30 mm below and 0.33 mm above to the next tray. The lid has 0.2 mm total stack relief. Do not mix versions.
- Pull eyes and lid locators do not establish arbitrary-orientation PCB retention; there is no independent PCB latch. Insert pullout strength and ESD are also unverified.
- The preceding no-latch statement describes original v2. V2-R adds PCB-edge keeper roofs and guide stops, two M2x20 tray ties and twelve M2x5 keeper screws. It retains intentional PCB clearance rather than forced clamping. Its checks cover rigid translations, not vibration, deformation or transport certification. Physical testing of v2-R is still outstanding.

## Build and validation
Use Python 3.12. Install `requirements.txt`, then run `python src/build_case.py` without `-O`. This exports nine STL files under `build/` and checks mesh, both assemblies, reference modules, 64 component-offset cases, maximum insert envelopes, coupon stacking, screw clearances and the assembled envelope. Inspect `build/verification.json` and the preview. There are no required global CAD applications or machine-specific cache paths.

For an intentional baseline update run `python src/build_case.py --output-dir models/v2`, review generated changes, and update source, artifacts, and documentation together. New incompatible variants should use a new model directory. Describe changes and validation in the PR; automated geometry checks do not replace slicing, printing, or fit testing.

For the retrofit, run `python src/build_retention.py --output-dir models/v2-retention`; optional `--models PATH` selects a freshly generated v2 source directory. The script also generates two upgrade print plates and a first-test plate. `src/retention_preview.py` renders mesh-based previews. Keep original v2 files intact and update the separate physical validation log with actual user evidence only.

For v3 run `python src/build_v3.py` (default `build/v3`), or intentionally regenerate with `--output-dir models/v3`. `--models` must point to v2-R, not original v2. Its local latch supports, 0.4 mm frame connecting strips and 0.1 mm peg fit require first-print checks; do not present geometric tests as mechanical life/force simulation. Plate 2 has only 4 mm gaps / 5.5 mm bed margins; other complete plates retain at least 8 mm. Keep the limited single-row tilt calculation distinct from a global density bound. Update `docs/validation-v3.md` only from actual user evidence.

V3 operating marks come from `src/operation_marks.py`: original rounded stroke glyphs, 0.55 mm stroke, 0.30 mm recess, about 3.55 mm letter height. No OS fonts. Preserve the physically correct opening direction (-Y) and press direction (-Z), layer pair labels and `LIFT` placement on rigid bars. Never engrave flexures, thin frame strips, locator holes or PCB contacts. The generator asserts each mark lies fully on a solid face. Keep `operation-guides.png`, print plates and the Bambu import report hashes in sync after changes.

## Provenance and publication
Retain dimension citations and distinguish assumptions from measured data. Do not add third-party PDFs, private workspace files, credentials, machine-specific paths, or user conversations. The project uses MIT for original contributions. Do not claim unperformed physical tests or certification.
