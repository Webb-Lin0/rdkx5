from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import time
from dataclasses import dataclass

from app.config import CONFIG


@dataclass(frozen=True)
class EdgeResponse:
    success: bool
    data: dict
    message: str = ""


class EdgeGatewayClient:
    def __init__(self, base_url: str | None = None, token: str | None = None, timeout: int = 30):
        self.base_url = (base_url or CONFIG.edge_api_base).rstrip("/")
        self.token = token if token is not None else CONFIG.edge_api_token
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict | None = None, timeout: int | None = None) -> dict:
        url = self.base_url + path
        data = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if payload is not None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}")
        except Exception as exc:
            raise RuntimeError(str(exc))

        obj = json.loads(raw)
        if isinstance(obj, dict) and obj.get("success") is False:
            raise RuntimeError(str(obj.get("message", "request failed")))
        return obj if isinstance(obj, dict) else {"data": obj}

    def send_page_command(self, page: str, action: str = "open", target: str = "", extra: dict | None = None) -> dict:
        payload = {"page": page, "action": action, "target": target, "ts": time.time()}
        if extra:
            payload.update(extra)
        return self._request("POST", "/api/ui/page-command", payload)

    def dispatch_voice(self, transcript: str, scene: str = "assistant", session_id: str = "") -> dict:
        return self._request(
            "POST",
            "/api/voice/dispatch",
            {"session_id": session_id, "scene": scene, "transcript": transcript, "language": "zh-CN", "device": "rdk"},
        )

    def fetch_weather(self, location: str = "") -> dict:
        return self._request("POST", "/api/weather/query", {"location": location})

    def generate_learning_questions(self, subject: str, seed: str = "") -> dict:
        return self._request("POST", "/api/learning/generate", {"subject": subject, "seed": seed})

    def explain_learning_question(self, question: str, options: list[str], selected: str = "") -> dict:
        return self._request("POST", "/api/learning/explain", {"question": question, "options": options, "selected": selected})

    def fetch_latest_homework(self, student_id: str, student_name: str) -> dict:
        query = urllib.parse.urlencode({"student_id": student_id, "student_name": student_name})
        return self._request("GET", f"/api/homework/latest?{query}")

    def submit_homework(self, homework_id: str, student_id: str, student_name: str, answers: list[dict]) -> dict:
        return self._request(
            "POST",
            "/api/homework/submit",
            {
                "homework_id": homework_id,
                "student_id": student_id,
                "student_name": student_name,
                "answers": answers,
            },
        )

    def explain_homework(self, question: str, options: list[str], answer: str = "") -> dict:
        return self._request("POST", "/api/homework/explain", {"question": question, "options": options, "answer": answer})

    def request_security_inspection(self, payload: dict) -> dict:
        return self._request("POST", "/api/security/inspection/request", payload)

    def upload_security_report(self, payload: dict, base_url: str | None = None) -> dict:
        if base_url:
            client = EdgeGatewayClient(base_url=base_url, token=self.token, timeout=self.timeout)
            return client._request("POST", "/api/security/inspection/upload", payload)
        return self._request("POST", "/api/security/inspection/upload", payload)

    def request_image_generation(self, prompt: str, style: str = "", size: str = "1024x768") -> dict:
        return self._request("POST", "/api/image/generate", {"prompt": prompt, "style": style, "size": size})

    def request_clockin(self, payload: dict) -> dict:
        return self._request("POST", "/api/attendance/clockin", payload)

    def request_posture_state(self, payload: dict | None = None) -> dict:
        return self._request("POST", "/api/posture/analyze", payload or {})

    def request_fitness_state(self, payload: dict | None = None) -> dict:
        return self._request("POST", "/api/fitness/analyze", payload or {})
