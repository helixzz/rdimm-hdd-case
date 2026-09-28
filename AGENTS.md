# Agent collaboration guide

## Project and source of truth
- This repository designs a printable RDIMM storage enclosure matching a traditional 3.5-inch HDD envelope and mounting positions.
- `src/build_case.py` is the parametric source of truth. `models/v1/` contains the committed printable baseline. `docs/printing.zh-CN.md` contains mechanical references, assumptions, and assembly instructions.
- Work from the latest main branch in a task branch. Read the current diff before editing; preserve other contributors' changes. Keep generated scratch output under ignored `build/`.

## Established design constraints
- Current outer envelope: 147 x 101.6 x 26 mm. Current capacity: 8, arranged 2+3+3. Units: mm.
- Reference module: 133.80 x 31.40 x 5.57 mm maximum envelope. This is a reference drawing, not verified exact Samsung M321RAJA0MB2-CCP geometry.
- The 2 mm component-free short PCB edges are an unverified assumption used by the clearance model. Do not silently turn this into a verified fact.
- HDD interfaces use 6-32 UNC; the model contains pilot holes, not finished threads. Preserve the documented 3.0 mm installed screw penetration limit unless the geometry and documentation are revised together.
- Never rescale the entire design to adjust printing fit: mounting coordinates must remain intentional.
- Do not infer chassis clearance for a taller variant, physical fit from a mesh check, ESD properties from ordinary filament, or the mathematical maximum capacity from this layout.

## Build and validation
Use Python 3.12. Install `requirements.txt`, then run `python src/build_case.py` without `-O`. This exports files under `build/` and asserts mesh/assembly/reference module/screw clearances. Inspect `build/verification.json` and the preview. There are no required global CAD applications or machine-specific cache paths.

For an intentional baseline update run `python src/build_case.py --output-dir models/v1`, review generated changes, and update source, artifacts, and documentation together. New incompatible variants should use a new model directory. Describe changes and validation in the PR; automated geometry checks do not replace slicing, printing, or fit testing.

## Provenance and publication
Retain dimension citations and distinguish assumptions from measured data. Do not add third-party PDFs, private workspace files, credentials, machine-specific paths, or user conversations. The project uses MIT for original contributions. Do not claim unperformed physical tests or certification.
