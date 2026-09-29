# Changelog

## v3 — experimental tool-free storage and backplane-clearance design

- Combine all three first-test groups into `first-test-all.stl`: seven pieces on one 256 mm bed, preserving print orientations, with at least 10 mm part gaps and 15 mm bed margins. Keep individual test files for replacements; add a mesh-derived plate preview and Bambu import verification.

- Engrave simple operating instructions directly into the cover, fixed body walls, tray end rails and paired retainer frames: press/open arrows, level icon, layer numbers, lift points and connector-end orientation. Use original 0.55 mm stroke lettering, 0.30 mm recesses and no external font dependency. Regenerate all plates and retainer lettering samples; preserve assembly interfaces and the 26 mm envelope.

- Remove mandatory interior hardware: three trays and three removable keyed PCB-edge retainer frames are captured by a closed sliding cover. Open trays must stay horizontal; they are not independently latching cartridges.
- Add 45-degree slide rails, a press-down anti-slide latch, optional cover reinforcement screws and finger access. Keep the 26 mm CAD height and eight-module capacity.
- Deepen side/bottom bores to 5.7/5.3 mm (+2 mm), with checked 5 mm intrusion. Offer separate thread-pilot and 3.6 mm locating-pin-clearance bodies.
- Add a 6 x 47 x 6.2 mm connector-end bottom recess as a trial clearance envelope, with a matching bottom tray. Actual fixed-backplane compatibility is unverified.
- Add mechanism/retainer first-test plates, a full-footprint empty fit gauge and three complete P2S plates. Local latch support and thin-wall slicing must be checked.
- Validate 512 module poses, 2048 frame-offset cases, 48 PCB stop controls, 64 retainer coupon cases, lid release sweep and both body options. Record a limited parallel-tilt study (6 or 7 modules under the stated assumptions); do not claim a global packing optimum.
- Preserve all previously printed v2 artifacts. No v3 physical, fatigue, impact, ESD or universal-bay-fit claims.

## v2-R — experimental carrying-retention retrofit

- Respond to a user print of v2 with noticeable carrying rattle; preserve the printed body and original v2 meshes.
- Replace trays/lid, add six PCB-edge keeper bars and short-edge guides, and connect the tray stack to the lid with two M2x20 screws. Add twelve M2x5 keeper screws; the existing four lid screws remain in use.
- Retain intentional PCB clearance instead of force-clamping memory. Add 512 reference translation cases, 48 physical-stop negative controls and 64 single-slot cases.
- Supply a first-test plate and two upgrade plates. Real fit, rattle reduction, thread strength and transport performance remain unverified.

## v2 — unprinted engineering prototype

- Keep the 147 × 101.6 × 26 mm envelope, 8-module capacity and mounting coordinates.
- Raise the short-edge shelves and increase tray pitch: nominal component-to-floor clearance improves from 0.10 to 0.30 mm; clearance to the next tray remains 0.33 mm.
- Reduce base/lid thickness and total stack relief to make room; shorten bottom pilot holes to preserve 0.7 mm of material behind them. V1 parts must not be mixed with v2.
- Add two lid locating collars, tray pull eyes and one/two/three tier marks.
- Offer a separate body with six side bores for PEM IUTB-632-150 inserts; retain bottom plastic pilots due to the edge-distance constraint.
- Add a three-tray single-slot stack coupon, flat cap, insert bore calibration coupon, mesh detail preview and physical validation checklist.
- Extend geometry checks to alternate body, maximum insert envelope, coupon stack, assembled envelope and 64 component-offset cases.
- Preserve v1 meshes and source as `src/build_v1.py`. No physical, orientation-retention, insert-strength or ESD claims are added.

## v1 — initial engineering prototype

- Three removable trays (2+3+3 RDIMMs), conventional HDD mounting pilots, M2-fastened lid, single-slot fit coupon and reference geometry checks.
