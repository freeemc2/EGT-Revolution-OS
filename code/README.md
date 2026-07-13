# code/ — Numerical Experiments and Controllers

Real code used in EGT numerical experiments and hardware control. MIT licensed (see `../LICENSE-CODE`).

## Files

- **`lattice-refinement.py`** — 3D cubic lattice with spacing `a`, 7-point discrete Laplacian (degree-6 connectivity), continuum profile `u(x) = C/|x|` with `C` pinned by boundary condition, discrete resonance measure B_res over the 7-point cavity. Real numerical physics that could be independently reproduced. Formerly `EGT Complete Operator/Python_Code/complete over view`.
- **`dragons-eye-controller.py`** — Python controller for the Dragons Eye hardware. Defines core constants (`PSI_FT = 12.09776`, `ETA_HARM = 0.875`, `SAT_CEILING = 0.8024`), implements `apply_egt_overwrite(jitter_level)` with numpy-based jitter modeling. Was `Verification_Logs/EGT_DRAGONS_EYE_V4.py` under the previous structure.
- **`bootstrap-project.py`** — utility script to scaffold a fresh EGT numerical experiment repository. Formerly `EGT Complete Operator/Python_Code/Repository_structure`.
- **`egt-kernel-v56_1.cpp`** — C++ kernel component. Small (< 2KB); role should be documented — currently a stub reference.

## Dependencies

See top-level `requirements.txt`. Core requirements: `numpy`, `matplotlib`, `pyserial` (for the Dragons Eye controller).

## What is NOT in this folder

- The Copilot-generated Protocol Omni stubs (`ai_monitor`, `muon_proof`, `omni_scale_collapse.py`) are in `_ai_artifacts_archive/`. They are not functional code.
- The bash wrapper `execute all experiments` that generated the `lattice-refinement.py` content is also in `_ai_artifacts_archive/`, since the useful output (the Python module) was extracted and the wrapper adds no scientific value.

## How to reproduce

```bash
pip install -r ../requirements.txt
python lattice-refinement.py    # runs the 7-point Laplacian refinement suite
# Dragons Eye controller requires the physical device on a COM port
```
