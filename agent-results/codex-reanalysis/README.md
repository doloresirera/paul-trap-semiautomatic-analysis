# Codex reanalysis

Independent reanalysis of the 11 experimental videos supplied with the lab
report. See [REPORTE_REANALISIS.md](REPORTE_REANALISIS.md) for the results,
assumptions, limitations, and comparison with the published values.

## Reproduce

1. Put the 11 `.mp4` input videos in this directory. They are intentionally
   not committed to keep the Git history small.
2. Create a Python environment and install `requirements.txt`.
3. Run `python analyze_trap.py`.

The script uses fixed random seeds and writes the CSV and PNG outputs in this
directory.
