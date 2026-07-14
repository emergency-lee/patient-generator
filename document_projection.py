"""Deterministic projections from a Patient Chronicle to Korean documents.

The Chronicle remains the source of truth; every projected field carries
``source_ids`` so consumers can trace it back to timeline/observation/problem
objects.  This module intentionally has no external dependencies.
"""
from __future__ import annotations
import json
from typing import Any, Dict, List


def _sid(prefix: str, index: int, item: Dict[str, Any]) -> str:
    return str(item.get("id") or item.get("source_id") or f"{prefix}-{index+1}")


def _observations(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    return c.get("observations") or []


def _obs_text(c: Dict[str, Any]) -> str:
    vals = []
    for i, o in enumerate(_observations(c)):
        name, value = o.get("name", "검사"), o.get("value", "미상")
        unit = o.get("unit") or ""
        vals.append(f"{name} {value}{unit}")
    return ", ".join(vals) if vals else "기록된 검사 결과 없음"


def narrative(c: Dict[str, Any]) -> Dict[str, Any]:
    """Create a readable Korean chart-style summary (one-column friendly)."""
    d = c.get("demographics", {})
    timeline = c.get("timeline") or []
    problems = c.get("problems") or []
    encounters = c.get("encounters") or []
    chief = timeline[0].get("event", "내원 사유 미상") if timeline else "내원 사유 미상"
    lines = [f"{d.get('age','연령 미상')}세 {d.get('sex','성별 미상')} 합성 환자({c.get('patient_id','unknown')})입니다.",
             f"주호소/현병력: {chief}"]
    if timeline:
        lines.append("경과: " + " → ".join(str(x.get("event", "")) for x in timeline))
    if problems:
        lines.append("과거력·활동성 문제: " + ", ".join(f"{p.get('label',p.get('code',''))}({p.get('status','상태 미상')})" for p in problems))
    lines.append("초기 활력·검사 관찰: " + _obs_text(c))
    # Optional domains are preserved when supplied by richer Chronicle versions.
    for key, label in (("medications","약물"),("allergies","알레르기"),("family_history","가족력"),("social_history","사회력"),("treatments","처치"),("disposition","퇴실/입원 경과")):
        if c.get(key) is not None:
            val = c[key]
            lines.append(f"{label}: {val if isinstance(val,str) else json.dumps(val,ensure_ascii=False)}")
    if encounters:
        lines.append("Encounter: " + "; ".join(str(e.get("type", "진료")) for e in encounters))
    return {"text": "\n".join(lines), "source_ids": {
        "timeline": [_sid("timeline",i,x) for i,x in enumerate(timeline)],
        "problems": [_sid("problem",i,x) for i,x in enumerate(problems)],
        "observations": [_sid("observation",i,x) for i,x in enumerate(_observations(c))],
        "encounters": [_sid("encounter",i,x) for i,x in enumerate(encounters)]}}


def project_chronicle(c: Dict[str, Any]) -> Dict[str, Any]:
    """Return 초진기록지, 구급활동일지, NEDIS-like record and narrative."""
    d, obs, tl = c.get("demographics", {}), _observations(c), c.get("timeline") or []
    sid = {"patient": [c.get("patient_id", "unknown")], "timeline": [_sid("timeline",i,x) for i,x in enumerate(tl)],
           "observations": [_sid("observation",i,x) for i,x in enumerate(obs)]}
    first = tl[0] if tl else {}
    initial = {o.get("name"): o.get("value") for o in obs}
    return {"synthetic": bool(c.get("synthetic", True)), "patient_id": c.get("patient_id"),
      "초진기록지": {"환자": d, "주호소": first.get("event", "미상"), "현병력": [x.get("event") for x in tl], "활력·검사": initial, "문제목록": c.get("problems", []), "source_ids": sid},
      "구급활동일지": {"환자": d, "신고/이송사유": first.get("event", "미상"), "현장경과": [x.get("details", x.get("event")) for x in tl], "관찰값": initial, "이송결과": c.get("disposition", "기록 없음"), "source_ids": sid},
      "NEDIS": {"patient_id": c.get("patient_id"), "sex": d.get("sex"), "age": d.get("age"), "chief_complaint": first.get("event", "unknown"), "observations": obs, "problems": c.get("problems", []), "encounters": c.get("encounters", []), "source_ids": sid},
      "narrative": narrative(c)}


__all__ = ["project_chronicle", "narrative"]

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--output-dir", default=".")
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text())
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    result = project_chronicle(data)
    (out / "projected_documents.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(out / "projected_documents.json")
