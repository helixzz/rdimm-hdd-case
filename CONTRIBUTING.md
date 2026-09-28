# Contributing

Issues and pull requests may be written in Chinese or English.

1. Clone the repository on each computer, fetch current `main`, and create a descriptive branch for the change. Avoid concurrent edits to the same branch across agents.
2. Install Python 3.12 dependencies with `python -m pip install -r requirements.txt` in a virtual environment.
3. Edit `src/build_case.py`; this is the source of truth. Keep units in mm. Explain any changed dimensions, tolerance assumptions, or hardware interfaces.
4. Run `python src/build_case.py`. Inspect the verification JSON, rendered preview, and affected STL files. If preparing a new printable baseline, run `python src/build_case.py --output-dir models/v1` and commit all corresponding artifacts together. Use a new version directory for an incompatible design.
5. Update the printing guide and README for material changes to fit, printing, hardware, or capacity. Do not promote physical-test status based on numerical checks.
6. Open a pull request stating the problem, design change, checks performed, and remaining physical validation. Keep unrelated changes separate.

The build itself checks manifold meshes, assembly intersections, reference module clearance, and screw intrusion. CI repeats that build on Windows and Linux. It does not slice the files or perform a print. Do not use optimized Python (`-O`), which disables assertions.

For physical feedback, report the model revision/commit, RAM part number, measured thickness if available, printer, filament, nozzle, layer height, slicer settings, and where fit fails. Never force a module into a tight slot. Photos should exclude serial numbers or other information you do not intend to publish.

The repository's MIT license applies to original contributed code, models, and documentation. Link third-party manufacturer drawings instead of copying them into the repository.
