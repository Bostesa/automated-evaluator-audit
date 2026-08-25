"""Fill power/volume tables and recommendation placeholder into docs/persuade_feasibility.md."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader((ROOT / "results/persuade_feasibility/power_planning.csv").open()))

alts = ["null", "weak", "moderate", "strong"]
ns = sorted({int(r["n"]) for r in rows})
by = {(int(r["n"]), r["alternative"]): r for r in rows}

lines = ["| n scored | mean ELL in sample | usable strata in sample | Type I (pi=0) | weak (pi=0.05) | moderate (pi=0.10) | strong (pi=0.20) |",
         "|---|---|---|---|---|---|---|"]
for n in ns:
    r0 = by[(n, "null")]
    cells = [f"{float(by[(n,a)]['rejection_rate']):.3f}" for a in alts]
    lines.append(f"| {n:,} | {float(r0['mean_n_ell_in_sample']):.0f} | {float(r0['mean_usable_strata_in_sample']):.0f} | " + " | ".join(cells) + " |")
lines.append("")
lines.append(f"500 replicates per cell, B = 999 permutations, alpha = 0.05; Monte Carlo SE on a rate near 0.8 is about 0.018, near 0.05 about 0.010.")
power_table = "\n".join(lines)

vol = ["| n scored | calls per judge-condition | x2 conditions | x4 conditions |", "|---|---|---|---|"]
for n in ns:
    vol.append(f"| {n:,} | {n:,} | {2*n:,} | {4*n:,} |")
volume_table = "\n".join(vol)

doc = ROOT / "docs/persuade_feasibility.md"
t = doc.read_text()
t = t.replace("<!-- POWER_TABLE -->", power_table)
t = t.replace("<!-- VOLUME_TABLE -->", volume_table)
doc.write_text(t)
print(power_table)
