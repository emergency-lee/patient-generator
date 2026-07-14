"""Small, dependency-free LLM connector.

Uses the OpenAI-compatible Responses API when OPENAI_API_KEY is present and
falls back to deterministic local generation otherwise. No credentials are
stored in files.
"""
import json, os, urllib.request, subprocess

class CodexConnector:
    def __init__(self, model=None, endpoint=None):
        self.model = model or os.getenv("CODEX_MODEL", "gpt-4.1-mini")
        self.endpoint = endpoint or os.getenv("CODEX_ENDPOINT", "https://api.openai.com/v1/responses")
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY")

    def generate(self, prompt: str, schema: dict) -> dict:
        # Local development path: use the authenticated Codex CLI when present.
        # This keeps prompts/data out of a second API integration.
        if os.getenv("LLM_CONNECTOR", "codex") == "codex" and self._codex_cli_available():
            return self._codex_generate(prompt, schema)
        if not self.api_key:
            return self._offline(schema)
        payload = {"model": self.model, "input": prompt,
                   "text": {"format": {"type": "json_schema", "name": "patient_chronicle",
                   "schema": schema, "strict": True}}}
        req = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode(),
                                     headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            body = json.loads(r.read())
        text = body.get("output_text")
        if not text:
            for item in body.get("output", []):
                for c in item.get("content", []):
                    if c.get("type") in ("output_text", "text"): text = c.get("text")
        if not text: raise RuntimeError("LLM 응답에 JSON 텍스트가 없습니다")
        return json.loads(text)

    def _codex_cli_available(self):
        try:
            return subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=5).returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    def _codex_generate(self, prompt, schema):
        instruction = (prompt + "\n출력은 JSON만. 아래 스키마를 준수하라:\n" +
                       json.dumps(schema, ensure_ascii=False))
        cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", instruction]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            raise RuntimeError("Codex CLI 실행 실패: " + result.stderr[-500:])
        raw = result.stdout.strip()
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Codex 응답에서 JSON을 찾지 못했습니다")
        return json.loads(raw[start:end + 1])

    def _offline(self, schema):
        # Safe demo record, explicitly marked synthetic.
        return {"patient_id":"SYN-0001","synthetic":True,"generated_by":"offline",
                "demographics":{"sex":"F","age":52,"residence":"서울"},
                "chief_complaint":"간헐적 흉부 불편감",
                "history_of_present_illness":"3개월 전부터 계단 오를 때 간헐적 발생, 휴식 시 호전",
                "past_medical_history":["고혈압 경계역 과거력"],
                "medications":[],"allergies":[],
                "family_history":[{"condition":"고혈압","relative":"부친"}],
                "social_history":{"smoking":"never","alcohol":"monthly","living_arrangement":"가족 동거"},
                "timeline":[{"date":"2026-01-12","event":"초진","source":"clinic","details":"3개월간 간헐적 흉부 불편감"}],
                "problems":[{"code":"R07.89","label":"기타 흉통","status":"active"}],
                "observations":[{"name":"혈압","value":"138/86","unit":"mmHg","date":"2026-01-12"}],
                "tests":[{"type":"심전도","result":"정상 동율동","interpretation":"급성 허혈 소견 없음","date":"2026-01-12"}],
                "interventions":[{"type":"교육","agent":"생활습관","response":"이해함","date":"2026-01-12"}],
                "disposition":{"status":"discharged","destination":"home","follow_up":"1주 내 외래","return_precautions":"흉통 악화 시 즉시 재내원"},
                "encounters":[],"provenance":{"consent":"simulation_only","version":"0.1"}}
