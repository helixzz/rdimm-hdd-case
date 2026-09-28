# Changelog

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
