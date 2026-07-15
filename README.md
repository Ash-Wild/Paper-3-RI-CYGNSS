# Paper-3-RI-CYGNSS
Paper 3 of my phd with RMIT university. Using ML to detect any patterns in GNSS-R signals during cyclone rapid intensification. 

## Keeping `requirements.txt` updated
- Run `python sync_requirements.py` from the project root.
- The script scans project `.py` files, finds imported third-party libraries, and rewrites `requirements.txt` with pinned versions from the active Python environment.
- If an import cannot be resolved to an installed package, it is listed at the bottom of `requirements.txt` for manual pinning.
