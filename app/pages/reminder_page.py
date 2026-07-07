from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QPushButton, QVBoxLayout, QWidget


class ReminderPage(QWidget):
    def __init__(self):
        super().__init__()
        base_dir = Path(__file__).resolve().parents[2] / "output"
        self.store_path = base_dir / "tasks.db"
        self.json_fallback = base_dir / "tasks.json"
        self.tasks: list[dict] = []
        self.selected_task: dict | None = None
        self.task_rows: list[QPushButton] = []
        self._build_ui()
        self.refresh()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(2000)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        left = QFrame()
        left.setStyleSheet("QFrame{background:#f8fbff;border:1px solid #dce7f5;border-radius:18px;}")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)
        self.title = QLabel("提醒日记")
        self.title.setStyleSheet("color:#1f2937;font-size:22px;font-weight:800;")
        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setFrameShape(QFrame.NoFrame)
        self.list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(8)
        self.list_scroll.setWidget(self.list_host)
        self.count_chip = QLabel("0")
        self.count_chip.setAlignment(Qt.AlignCenter)
        self.count_chip.setFixedWidth(76)
        self.count_chip.setStyleSheet("background:#eff6ff;border:1px solid #bfdbfe;border-radius:16px;color:#2563eb;font-weight:800;padding:8px 0;")
        self.refresh_btn = QPushButton("刷新提醒")
        self.refresh_btn.clicked.connect(self.refresh)
        self.delete_btn = QPushButton("删除任务")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn.clicked.connect(self.delete_selected)
        row = QHBoxLayout()
        row.addWidget(self.count_chip)
        row.addWidget(self.delete_btn)
        row.addWidget(self.edit_btn)
        left_layout.addWidget(self.title)
        left_layout.addWidget(self.list_scroll, 1)
        left_layout.addWidget(self.refresh_btn)
        left_layout.addLayout(row)

        right = QFrame()
        right.setStyleSheet("QFrame{background:#ffffff;border:1px solid #dce7f5;border-radius:18px;}")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(18, 18, 18, 18)
        right_layout.setSpacing(12)
        self.detail_title = QLabel("任务详情")
        self.detail_title.setStyleSheet("color:#1f2937;font-size:24px;font-weight:800;")
        self.detail_created = QLabel("")
        self.detail_execute = QLabel("")
        self.detail_freq = QLabel("")
        self.detail_status = QLabel("")
        self.detail_message = QLabel("")
        self.detail_message.setWordWrap(True)
        for widget in (self.detail_created, self.detail_execute, self.detail_freq, self.detail_status, self.detail_message):
            right_layout.addWidget(widget)
        right_layout.addStretch(1)

        root.addWidget(left, 7)
        root.addWidget(right, 4)

    @staticmethod
    def _fmt_dt(value: str) -> str:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return value or "-"

    @staticmethod
    def _task_message(task: dict) -> str:
        args = task.get("script_args", "[]")
        try:
            parsed = json.loads(args) if isinstance(args, str) else (args or [])
        except Exception:
            parsed = []
        if isinstance(parsed, list) and "--message" in parsed:
            idx = parsed.index("--message")
            if idx + 1 < len(parsed):
                return str(parsed[idx + 1])
        for key in ("message", "task", "content", "note"):
            value = task.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return "无内容"

    def _status_text(self, task: dict) -> str:
        if task.get("status") == "done":
            return "已完成"
        value = task.get("execute_at") or task.get("created_at") or ""
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            return "已完成" if dt <= datetime.now() else "待完成"
        except Exception:
            return "待完成"

    def _load_sqlite(self):
        if not self.store_path.exists():
            return []
        try:
            conn = sqlite3.connect(str(self.store_path), timeout=2)
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute("SELECT * FROM tasks ORDER BY execute_at ASC, created_at ASC").fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()
        except Exception:
            return []

    def _load_json(self):
        if not self.json_fallback.exists():
            return []
        try:
            data = json.loads(self.json_fallback.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save_json(self):
        self.json_fallback.parent.mkdir(parents=True, exist_ok=True)
        self.json_fallback.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")

    def _make_row(self, task: dict) -> QPushButton:
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(64)
        btn.setMaximumHeight(64)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setProperty("task_id", str(task.get("task_id", "")))
        status = self._status_text(task)
        btn.setText(f"{self._fmt_dt(str(task.get('execute_at') or task.get('created_at') or '--'))[:16]}  {self._task_message(task)}\n{status}")
        btn.setStyleSheet(
            "QPushButton{background:#fff;border:1px solid #dbe6f7;border-radius:16px;text-align:left;padding:10px 14px;color:#374151;font-size:13px;font-weight:700;}"
            "QPushButton:hover{border-color:#aac5f0;}"
            "QPushButton:checked{background:#fff4f5;border-color:#f2c3cc;}"
        )
        return btn

    def refresh(self):
        self.tasks = self._load_sqlite() or self._load_json()
        self.count_chip.setText(str(len(self.tasks)))
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.task_rows = []

        if not self.tasks:
            empty = QLabel("暂无任务")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet("color:#94a3b8;font-size:12px;font-weight:700;")
            self.list_layout.addWidget(empty)
            self._clear_detail()
            return

        for task in self.tasks:
            row = self._make_row(task)
            row.clicked.connect(lambda checked=False, current=task: self._select_task(current))
            self.task_rows.append(row)
            self.list_layout.addWidget(row)
        self.list_layout.addStretch(1)
        selected_id = self.selected_task.get("task_id") if self.selected_task else None
        chosen = next((task for task in self.tasks if task.get("task_id") == selected_id), self.tasks[0])
        self._select_task(chosen)

    def _clear_detail(self):
        self.detail_title.setText("任务详情")
        self.detail_created.setText("")
        self.detail_execute.setText("")
        self.detail_freq.setText("")
        self.detail_status.setText("")
        self.detail_message.setText("")

    def _select_task(self, task: dict):
        self.selected_task = task
        task_id = str(task.get("task_id", ""))
        for row in self.task_rows:
            row.setChecked(str(row.property("task_id") or "") == task_id)
        self.detail_title.setText(f"任务详情 - {task.get('title', '提醒')}")
        self.detail_created.setText(f"创建时间: {self._fmt_dt(str(task.get('created_at', '')))}")
        self.detail_execute.setText(f"提醒时间: {self._fmt_dt(str(task.get('execute_at', '')))}")
        self.detail_freq.setText("重复：每天" if task.get("task_type") == "cron" else "重复：单次")
        self.detail_status.setText(f"状态: {self._status_text(task)}")
        self.detail_message.setText(f"备注: {self._task_message(task)}")

    def delete_selected(self):
        if not self.selected_task:
            return
        task_id = self.selected_task.get("task_id")
        self.tasks = [task for task in self.tasks if task.get("task_id") != task_id]
        self._save_json()
        self.selected_task = None
        self.refresh()
