import argparse, json, pathlib, subprocess, sys
from codex_connector import CodexConnector

ROOT = pathlib.Path(__file__).parent
SCHEMA = json.loads((ROOT / "schema.json").read_text())

def build_prompt(args):
    return (f"한국어 의료 시뮬레이션용 합성 환자 chronicle을 생성하라. 환자 수={args.count}. "
            "극적 사건을 과도하게 만들지 말고 일반 인구 분포를 따른다. 개인정보·실제 환자 추정은 금지. "
            "반드시 제공된 JSON schema에 맞는 JSON 하나만 출력하고 synthetic=true로 표시하라.")

def main():
    p=argparse.ArgumentParser(description="Synthetic patient chronicle generator")
    p.add_argument("-n","--count",type=int,default=1); p.add_argument("-o","--output",default="patient_chronicle.json")
    p.add_argument("--validate",action="store_true"); p.add_argument("--project",action="store_true")
    a=p.parse_args(); connector=CodexConnector(); records=[]
    for i in range(max(1,a.count)):
        data=connector.generate(build_prompt(a)+f"\n이번 사례 번호: {i+1}", SCHEMA); records.append(data)
    payload=records[0] if a.count == 1 else {"synthetic":True,"count":len(records),"records":records}
    pathlib.Path(a.output).write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    if a.validate:
        cmd=[sys.executable,str(ROOT/"validate_chronicle.py"),"-i",a.output]
        subprocess.run(cmd,check=True)
    if a.project and a.count == 1:
        subprocess.run([sys.executable,str(ROOT/"document_projection.py"),a.output,"--output-dir",str(pathlib.Path(a.output).parent)],check=True)
    print(f"생성 완료: {a.output} (records={len(records)}, synthetic={payload.get('synthetic')})")
if __name__ == "__main__": main()
