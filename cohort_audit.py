#!/usr/bin/env python3
"""Small distribution audit for a Chronicle cohort (stdlib only)."""
import argparse, json
from pathlib import Path
from collections import Counter
from validate_chronicle import validate

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("-i","--input",required=True); ap.add_argument("-o","--output")
    a=ap.parse_args(); data=json.loads(Path(a.input).read_text())
    if isinstance(data, dict) and isinstance(data.get("records"), list): cohort=data["records"]
    else: cohort=data if isinstance(data,list) else [data]
    ages=[c.get("demographics",{}).get("age") for c in cohort if isinstance(c,dict)]
    report={"total":len(cohort),"synthetic_rate":sum(c.get("synthetic") is True for c in cohort if isinstance(c,dict))/max(1,len(cohort)),"sex_distribution":dict(Counter(c.get("demographics",{}).get("sex","UNKNOWN") for c in cohort if isinstance(c,dict))),"problem_status_distribution":dict(Counter(p.get("status","UNKNOWN") for c in cohort if isinstance(c,dict) for p in c.get("problems",[]) if isinstance(p,dict))),"validation":{}}
    report["validation"]={"valid_count":sum(validate(c)["valid"] for c in cohort),"invalid_count":sum(not validate(c)["valid"] for c in cohort)}
    ages=[x for x in ages if isinstance(x,(int,float))]
    if ages: report["age"]={"min":min(ages),"max":max(ages),"mean":round(sum(ages)/len(ages),2)}
    out=json.dumps(report,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(out)
    print(out)
if __name__=="__main__": main()
