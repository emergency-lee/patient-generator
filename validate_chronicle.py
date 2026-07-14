#!/usr/bin/env python3
"""Dependency-free quality gate for Patient Chronicle JSON.

Usage: python validate_chronicle.py -i patient_chronicle.json -o validation_report.json
Accepts one chronicle object or a JSON array/cohort.
"""
import argparse, json, re
from datetime import datetime
from pathlib import Path

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

def _date(value):
    if not isinstance(value, str): return None
    m = DATE_RE.search(value)
    if not m: return None
    try: return datetime.strptime(m.group(), "%Y-%m-%d").date()
    except ValueError: return None

def validate(c, index=0):
    errors, warnings = [], []
    def err(code, msg): errors.append({"code": code, "message": msg})
    def warn(code, msg): warnings.append({"code": code, "message": msg})
    if not isinstance(c, dict):
        return {"index": index, "patient_id": None, "valid": False,
                "errors": [{"code":"TYPE", "message":"chronicle must be an object"}], "warnings": []}
    pid = c.get("patient_id")
    for key in ("patient_id","demographics","timeline","problems","observations","encounters","provenance"):
        if key not in c: err("REQUIRED", f"missing required field: {key}")
    if c.get("synthetic") is not True: err("SYNTHETIC_MARKER", "synthetic must be true")
    if not isinstance(c.get("provenance"), dict): err("PROVENANCE", "provenance must be an object")
    else:
        for key in ("version",):
            if not c["provenance"].get(key): warn("PROVENANCE_INCOMPLETE", f"provenance.{key} is missing")
        if not any(c["provenance"].get(k) for k in ("generator","model","generated_at","seed","version")):
            warn("PROVENANCE_INCOMPLETE", "no generator/model/time/seed provenance recorded")
    d = c.get("demographics")
    if isinstance(d, dict):
        for key in ("sex","age","residence"):
            if key not in d: err("DEMOGRAPHICS_REQUIRED", f"demographics.{key} missing")
        if not isinstance(d.get("age"), int) or not 0 <= d.get("age", -1) <= 120: err("AGE_RANGE", "demographics.age must be integer 0..120")
    # Timeline must be chronological; malformed dates are explicitly reported.
    tl = c.get("timeline", [])
    dates = []
    if not isinstance(tl, list): err("TYPE", "timeline must be an array")
    else:
        for i, e in enumerate(tl):
            if not isinstance(e, dict): err("TIMELINE_ITEM", f"timeline[{i}] must be object"); continue
            dt = _date(e.get("date"));
            if dt is None: err("DATE_FORMAT", f"timeline[{i}].date is not ISO date")
            else: dates.append((dt, i))
            if not e.get("source"): err("SOURCE_REQUIRED", f"timeline[{i}].source missing")
        for (a, ai), (b, bi) in zip(dates, dates[1:]):
            if b < a: err("TEMPORAL_ORDER", f"timeline[{bi}] precedes timeline[{ai}]")
    # Observations cannot predate the first timeline event when a timeline exists.
    first = min((x[0] for x in dates), default=None)
    for i, o in enumerate(c.get("observations", []) if isinstance(c.get("observations"), list) else []):
        od = _date(o.get("date")) if isinstance(o, dict) else None
        if od is None: err("DATE_FORMAT", f"observations[{i}].date is not ISO date")
        elif first and od < first: warn("OUTSIDE_TIMELINE", f"observations[{i}] predates first timeline event")
    # Basic future leakage: an encounter record must not mention later dated observations/events.
    encs = c.get("encounters", [])
    if isinstance(encs, list):
        future_dates = [_date(x.get("date")) for x in tl if isinstance(x,dict)] + [_date(x.get("date")) for x in c.get("observations",[]) if isinstance(x,dict)]
        future_dates = [x for x in future_dates if x]
        for i, e in enumerate(encs):
            if not isinstance(e, dict): continue
            ed = _date(e.get("date")); rec = e.get("record", "")
            if ed and isinstance(rec, str):
                mentioned = [_date(x.group()) for x in DATE_RE.finditer(rec)]
                if any(x > ed for x in mentioned): err("FUTURE_LEAKAGE", f"encounters[{i}].record mentions date after encounter")
    return {"index": index, "patient_id": pid, "valid": not errors, "errors": errors, "warnings": warnings}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("-i","--input",required=True); ap.add_argument("-o","--output")
    a = ap.parse_args(); data = json.loads(Path(a.input).read_text())
    if isinstance(data, dict) and isinstance(data.get("records"), list):
        cohort = data["records"]
    else:
        cohort = data if isinstance(data, list) else [data]
    results = [validate(c, i) for i, c in enumerate(cohort)]
    report = {"valid": all(r["valid"] for r in results), "total": len(results), "valid_count": sum(r["valid"] for r in results), "results": results}
    out = json.dumps(report, ensure_ascii=False, indent=2)
    if a.output: Path(a.output).write_text(out)
    print(out)
    raise SystemExit(0 if report["valid"] else 1)
if __name__ == "__main__": main()
