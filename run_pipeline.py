#!/usr/bin/env python3
"""Run the local Patient Chronicle quality-gated pipeline."""
import argparse, json, pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--count", type=int, default=1)
    ap.add_argument("-o", "--output-dir", default="run-output")
    args = ap.parse_args(); out = pathlib.Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    cohort = out / "chronicle.json"
    subprocess.run([sys.executable, str(ROOT/"app.py"), "-n", str(args.count), "-o", str(cohort)], check=True)
    # The app wraps cohorts as {records:[...]}; validators accept both forms.
    validation = out / "validation_report.json"
    with validation.open("w") as f:
        subprocess.run([sys.executable, str(ROOT/"validate_chronicle.py"), "-i", str(cohort)], stdout=f, check=True)
    audit = out / "cohort_report.json"
    with audit.open("w") as f:
        subprocess.run([sys.executable, str(ROOT/"cohort_audit.py"), "-i", str(cohort)], stdout=f, check=True)
    if args.count == 1:
        subprocess.run([sys.executable, str(ROOT/"document_projection.py"), str(cohort), "--output-dir", str(out)], check=True)
    manifest = {"synthetic": True, "count": args.count, "artifacts": [p.name for p in out.iterdir()], "quality_gate": "passed_local"}
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
