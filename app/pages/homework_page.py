from __future__ import annotations

import json

from PyQt5.QtCore import Qt, QThreadPool
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.config import CONFIG
from app.interfaces.edge_gateway import EdgeGatewayClient
from app.workers import JsonWorker


class HomeworkPage(QWidget):
    def __init__(self, client: EdgeGatewayClient | None = None):
        super().__init__()
        self.client = client or EdgeGatewayClient()
        self.pool = QThreadPool.globalInstance()
        self.homework = None
        self.index = 0
        self.answers: dict[str, str] = {}
        self._build_ui()
        self.load_latest()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        left = QFrame()
        left.setStyleSheet("QFrame{background:#fff;border:1px solid #d7e7f3;border-radius:18px;}")
        left_layout = QVBoxLayout(left)
        self.title = QLabel("作业布置")
        self.question = QLabel("等待作业接口返回")
        self.question.setWordWrap(True)
        self.question.setStyleSheet("font-size:16px;font-weight:700;color:#29455d;")
        self.options_box = QVBoxLayout()
        self.refresh_btn = QPushButton("刷新作业")
        self.submit_btn = QPushButton("提交答案")
        self.prev_btn = QPushButton("上一题")
        self.next_btn = QPushButton("下一题")
        self.explain_btn = QPushButton("请求讲解")
        self.refresh_btn.clicked.connect(self.load_latest)
        self.submit_btn.clicked.connect(self.submit_answers)
        self.prev_btn.clicked.connect(self.prev_question)
        self.next_btn.clicked.connect(self.next_question)
        self.explain_btn.clicked.connect(self.explain_current)
        nav = QHBoxLayout()
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.next_btn)
        left_layout.addWidget(self.title)
        left_layout.addWidget(self.refresh_btn)
        left_layout.addWidget(self.question)
        left_layout.addLayout(self.options_box)
        left_layout.addLayout(nav)
        left_layout.addWidget(self.explain_btn)
        left_layout.addWidget(self.submit_btn)

        right = QFrame()
        right.setStyleSheet("QFrame{background:#fff;border:1px solid #d7e7f3;border-radius:18px;}")
        right_layout = QVBoxLayout(right)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        right_layout.addWidget(QLabel("作业结果"))
        right_layout.addWidget(self.output, 1)
        root.addWidget(left, 8)
        root.addWidget(right, 4)

    def _clear_options(self):
        while self.options_box.count():
            item = self.options_box.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

    def _normalize_homework(self, obj):
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        if not isinstance(data, dict):
            return None
        questions = []
        for idx, item in enumerate(data.get("questions", []) if isinstance(data.get("questions", []), list) else []):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question", "")).strip()
            options = item.get("options", [])
            if not question or not isinstance(options, list):
                continue
            normalized = [str(opt).strip() for opt in options[:4]]
            if len(normalized) < 4:
                continue
            questions.append(
                {
                    "question_id": str(item.get("question_id", f"q{idx+1}")).strip(),
                    "question": question,
                    "options": normalized,
                    "answer": str(item.get("answer", "")).strip().upper()[:1],
                    "explanation": str(item.get("explanation", "")).strip(),
                }
            )
        data["questions"] = questions
        return data if questions else None

    def _build_submit_payload(self) -> list[dict]:
        answers = []
        if not self.homework:
            return answers
        for item in self.homework.get("questions", []):
            qid = str(item.get("question_id", "")).strip()
            if qid in self.answers:
                answers.append({"question_id": qid, "choice": self.answers[qid]})
        return answers

    def _format_response_text(self, obj) -> str:
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, dict):
            if data.get("score") is not None and data.get("total") is not None:
                return f"提交成功，得分 {data.get('score')}/{data.get('total')}"
            for key in ("reply_text", "text", "content", "explanation", "result"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    def load_latest(self):
        worker = JsonWorker(lambda: self.client.fetch_latest_homework(CONFIG.default_student_id, CONFIG.default_student_name))
        worker.signals.success.connect(self._on_homework)
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def _on_homework(self, obj):
        self.homework = self._normalize_homework(obj)
        self.index = 0
        self.answers = {}
        self.render_question()

    def _on_error(self, message: str):
        self.homework = None
        self.output.setPlainText(message)
        self.question.setText("暂无作业")

    def render_question(self):
        self._clear_options()
        if not self.homework:
            self.question.setText("暂无作业")
            return
        questions = self.homework.get("questions", [])
        if not questions:
            self.question.setText("暂无作业")
            return
        self.index = max(0, min(self.index, len(questions) - 1))
        item = questions[self.index]
        self.question.setText(f"{self.index + 1}. {item.get('question', '')}")
        for idx, opt in enumerate(item.get("options", [])[:4]):
            tag = chr(ord("A") + idx)
            btn = QPushButton(f"{tag}. {opt}")
            btn.setCheckable(True)
            btn.toggled.connect(lambda checked, qid=str(item.get("question_id", "")), t=tag: self._set_answer(qid, t, checked))
            self.options_box.addWidget(btn)
        self.prev_btn.setEnabled(self.index > 0)
        self.next_btn.setEnabled(self.index + 1 < len(questions))

    def _set_answer(self, qid: str, choice: str, checked: bool):
        if checked and qid:
            self.answers[qid] = choice

    def prev_question(self):
        if self.homework and self.index > 0:
            self.index -= 1
            self.render_question()

    def next_question(self):
        if self.homework and self.index + 1 < len(self.homework.get("questions", [])):
            self.index += 1
            self.render_question()

    def explain_current(self):
        if not self.homework:
            return
        item = self.homework.get("questions", [])[self.index]
        options = list(item.get("options", []))
        answer = self.answers.get(str(item.get("question_id", "")), "")
        worker = JsonWorker(lambda: self.client.explain_homework(item.get("question", ""), options, answer))
        worker.signals.success.connect(lambda obj: self.output.setPlainText(self._format_response_text(obj)))
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def submit_answers(self):
        if not self.homework:
            return
        answers = self._build_submit_payload()
        worker = JsonWorker(
            lambda: self.client.submit_homework(
                str(self.homework.get("homework_id", "")),
                CONFIG.default_student_id,
                CONFIG.default_student_name,
                answers,
            )
        )
        worker.signals.success.connect(lambda obj: self.output.setPlainText(self._format_response_text(obj)))
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

