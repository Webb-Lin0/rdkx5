from __future__ import annotations

import json

from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.interfaces.edge_gateway import EdgeGatewayClient
from app.workers import JsonWorker


SUBJECTS = {
    "history": "中国历史",
    "culture": "传统文化",
    "math": "数学学习",
    "english": "英语学习",
}


class LearningPage(QWidget):
    def __init__(self, client: EdgeGatewayClient | None = None):
        super().__init__()
        self.client = client or EdgeGatewayClient()
        self.pool = QThreadPool.globalInstance()
        self.questions: list[dict] = []
        self.current_index = 0
        self.selected: dict[str, str] = {}
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        left = QFrame()
        left.setStyleSheet("QFrame{background:#fff;border:1px solid #d7e7f3;border-radius:18px;}")
        left_layout = QVBoxLayout(left)
        self.header = QLabel("通识学习")
        self.header.setStyleSheet("font-size:22px;font-weight:800;color:#1f4f72;")
        self.question = QLabel("请选择主题后向边缘设备请求题目")
        self.question.setWordWrap(True)
        self.question.setStyleSheet("font-size:16px;color:#29455d;font-weight:700;")
        self.options_box = QVBoxLayout()
        self.ask_ai_btn = QPushButton("请求讲解")
        self.ask_ai_btn.clicked.connect(self.explain_current)
        self.prev_btn = QPushButton("上一题")
        self.next_btn = QPushButton("下一题")
        self.prev_btn.clicked.connect(self.show_previous)
        self.next_btn.clicked.connect(self.show_next)
        nav = QHBoxLayout()
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        left_layout.addWidget(self.header)
        for key, label in SUBJECTS.items():
            btn = QPushButton(label)
            btn.clicked.connect(lambda _=False, s=key: self.generate_questions(s))
            left_layout.addWidget(btn)
        left_layout.addWidget(self.question)
        left_layout.addLayout(self.options_box)
        left_layout.addWidget(self.ask_ai_btn)
        left_layout.addLayout(nav)

        right = QFrame()
        right.setStyleSheet("QFrame{background:#fff;border:1px solid #d7e7f3;border-radius:18px;}")
        right_layout = QVBoxLayout(right)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(QLabel("讲解 / 返回结果"))
        right_layout.addWidget(self.output, 1)
        root.addWidget(left, 8)
        root.addWidget(right, 4)

    def _clear_options(self):
        while self.options_box.count():
            item = self.options_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _prepare_learning_request(self, subject: str) -> dict:
        key = str(subject or "").strip().lower()
        return {"subject": key if key in SUBJECTS else "history", "seed": "20260706", "client": "rdk_share"}

    def _extract_questions(self, obj) -> list[dict]:
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            return []
        rows = data.get("questions") or data.get("items") or []
        if isinstance(rows, dict):
            rows = rows.get("questions") or []
        result = []
        for idx, item in enumerate(rows if isinstance(rows, list) else []):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            options = item.get("options", [])
            if not question or not isinstance(options, list):
                continue
            normalized = [str(opt).strip() for opt in options[:4]]
            if len(normalized) < 4:
                continue
            result.append(
                {
                    "question_id": str(item.get("question_id", f"q{idx+1}")).strip(),
                    "question": question,
                    "options": normalized,
                    "answer": str(item.get("answer", "")).strip().upper()[:1],
                    "explanation": str(item.get("explanation", "")).strip(),
                }
            )
        return result

    def _format_response_text(self, obj) -> str:
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, dict):
            for key in ("reply_text", "text", "content", "explanation", "result"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    def generate_questions(self, subject: str):
        self.output.setPlainText("正在请求题目...")
        req = self._prepare_learning_request(subject)
        worker = JsonWorker(lambda: self.client.generate_learning_questions(req["subject"], req["seed"]))
        worker.signals.success.connect(self._on_questions)
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def _on_questions(self, obj):
        self.questions = self._extract_questions(obj)
        self.current_index = 0
        self.selected = {}
        self.render_question()

    def _on_error(self, message: str):
        self.output.setPlainText(message)

    def render_question(self):
        self._clear_options()
        if not self.questions:
            self.question.setText("暂无题目")
            return
        item = self.questions[self.current_index]
        self.question.setText(f"{self.current_index + 1}. {item.get('question', '')}")
        for idx, opt in enumerate(item.get("options", [])[:4]):
            tag = chr(ord("A") + idx)
            btn = QPushButton(f"{tag}. {opt}")
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, t=tag: self._set_selected(t, checked))
            self.options_box.addWidget(btn)
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index + 1 < len(self.questions))

    def _set_selected(self, tag: str, checked: bool):
        if checked and self.questions:
            qid = str(self.questions[self.current_index].get("question_id", self.current_index))
            self.selected[qid] = tag

    def explain_current(self):
        if not self.questions:
            return
        item = self.questions[self.current_index]
        options = list(item.get("options", []))
        selected = self.selected.get(str(item.get("question_id", self.current_index)), "")
        worker = JsonWorker(lambda: self.client.explain_learning_question(item.get("question", ""), options, selected))
        worker.signals.success.connect(lambda obj: self.output.setPlainText(self._format_response_text(obj)))
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.render_question()

    def show_next(self):
        if self.current_index + 1 < len(self.questions):
            self.current_index += 1
            self.render_question()

