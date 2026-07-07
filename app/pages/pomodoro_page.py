from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QBrush, QFont, QPainter
from PyQt5.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget


DEFAULT_RECORDS = [
    ("听音乐", 1),
    ("看书", 2),
    ("学英语", 3),
    ("学单片机", 3),
    ("休息", 1),
]


class FocusChartDialog(QDialog):
    def __init__(self, records: list[dict], parent=None):
        super().__init__(parent)
        self.records = records
        self.setWindowTitle("今日专注时间分布")
        self.setMinimumSize(520, 540)
        self.setStyleSheet("QDialog{background:#f6fbff;border-radius:20px;}")

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(20, 20, -20, -20)
        center = QPointF(rect.center())
        radius = min(rect.width(), rect.height()) * 0.28
        total = sum(max(0.0, float(item.get("hours", 0))) for item in self.records) or 1.0
        colors = ["#b3e5ff", "#c8e6c9", "#ffe0b2", "#d1c4e9", "#ffccbc", "#bbdefb", "#dcedc8", "#f8bbd0"]

        painter.setPen(Qt.NoPen)
        start_angle = 0.0
        for idx, item in enumerate(self.records):
            hours = max(0.0, float(item.get("hours", 0)))
            if hours <= 0:
                continue
            span = 360.0 * hours / total
            painter.setBrush(QBrush(QColor(colors[idx % len(colors)])))
            painter.drawPie(
                int(center.x() - radius),
                int(center.y() - radius),
                int(radius * 2),
                int(radius * 2),
                int(start_angle * 16),
                int(span * 16),
            )
            start_angle += span

        y = int(center.y() + radius + 42)
        painter.setFont(QFont("Sans Serif", 11, QFont.Bold))
        for idx, item in enumerate(self.records):
            title = str(item.get("name", "")).strip()
            hours = item.get("hours", 0)
            painter.setBrush(QBrush(QColor(colors[idx % len(colors)])))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(int(rect.left() + 35), y - 12, 16, 16, 4, 4)
            painter.setPen(QColor("#35566f"))
            painter.drawText(int(rect.left() + 60), y + 2, f"{title}  {hours}小时")
            y += 28


class PomodoroPage(QWidget):
    def __init__(self):
        super().__init__()
        self.state_path = Path(__file__).resolve().parents[2] / "output" / "pomodoro_state.json"
        self.focus_minutes = 25
        self.break_minutes = 5
        self.remaining_seconds = self.focus_minutes * 60
        self.is_running = False
        self.is_focus_mode = True
        self.history: list[dict] = []
        self._build_ui()
        self._load_state()
        self._refresh_ui()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _build_ui(self):
        self.root_layout = QHBoxLayout(self)
        self.root_layout.setContentsMargins(10, 10, 10, 10)
        self.root_layout.setSpacing(10)

        self.left_shell = QFrame()
        self.left_shell.setStyleSheet("QFrame{background:#f5faff;border:1px solid #d9e9f5;border-radius:22px;}")
        self.left_layout = QVBoxLayout(self.left_shell)
        self.left_layout.setContentsMargins(14, 14, 14, 14)
        self.left_layout.setSpacing(10)

        self.hero_card = QFrame()
        self.hero_card.setStyleSheet("QFrame{background:#eef8ff;border:2px solid #cfe7f7;border-radius:26px;}")
        self.hero_layout = QVBoxLayout(self.hero_card)
        self.hero_layout.setContentsMargins(18, 18, 18, 16)
        self.hero_layout.setSpacing(8)

        self.timer_label = QLabel("25:00")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("background:transparent;color:#2f77a8;font-size:60px;font-weight:900;")

        self.status_chip = QLabel("状态：待开始")
        self.status_chip.setAlignment(Qt.AlignCenter)
        self.status_chip.setStyleSheet("background:#ffffff;border:1px solid #d7e7f3;border-radius:15px;color:#4e6f88;font-size:13px;font-weight:800;padding:6px 18px;")
        self.hero_layout.addWidget(self.timer_label, 1)
        self.hero_layout.addWidget(self.status_chip, 0, Qt.AlignHCenter)

        self.task_card = QFrame()
        self.task_card.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d7e7f3;border-radius:18px;}")
        self.task_layout = QVBoxLayout(self.task_card)
        self.task_layout.setContentsMargins(12, 9, 12, 10)
        self.task_layout.setSpacing(6)
        self.task_title = QLabel("当前任务")
        self.task_title.setStyleSheet("color:#35617f;font-size:12px;font-weight:800;")
        self.task_edit = QLineEdit()
        self.task_edit.setPlaceholderText("例如：背单词 / 写作业 / 阅读")
        self.task_edit.setStyleSheet("QLineEdit{background:#f7fbff;border:1px solid #d9e7f3;border-radius:12px;color:#39576f;padding:8px 10px;font-size:13px;}")
        self.task_layout.addWidget(self.task_title)
        self.task_layout.addWidget(self.task_edit)

        self.duration_row = QHBoxLayout()
        self.duration_row.setContentsMargins(0, 0, 0, 0)
        self.duration_row.setSpacing(10)

        self.focus_spin = QSpinBox()
        self.focus_spin.setRange(1, 120)
        self.focus_spin.setValue(self.focus_minutes)
        self.focus_spin.setSuffix(" 分钟")
        self.break_spin = QSpinBox()
        self.break_spin.setRange(1, 60)
        self.break_spin.setValue(self.break_minutes)
        self.break_spin.setSuffix(" 分钟")
        for spin in (self.focus_spin, self.break_spin):
            spin.setStyleSheet("QSpinBox{background:#f7fbff;border:1px solid #d9e7f3;border-radius:12px;color:#39576f;padding:6px 8px;font-size:13px;}")

        self.focus_card = self._duration_card("专注时长", self.focus_spin)
        self.break_card = self._duration_card("休息时长", self.break_spin)
        self.duration_row.addWidget(self.focus_card)
        self.duration_row.addWidget(self.break_card)

        self.button_row = QHBoxLayout()
        self.button_row.setContentsMargins(0, 0, 0, 0)
        self.button_row.setSpacing(10)
        self.start_btn = QPushButton("开始")
        self.pause_btn = QPushButton("暂停")
        self.reset_btn = QPushButton("重置")
        for btn, color1, color2, border in (
            (self.start_btn, "#67c7ff", "#57b9ef", "#3aa2dc"),
            (self.pause_btn, "#dceffd", "#cfe7f7", "#b9d6ea"),
            (self.reset_btn, "#ffffff", "#f2f8fd", "#cfdfee"),
        ):
            btn.setStyleSheet(f"QPushButton{{background:{color1};border:1px solid {border};border-radius:18px;color:#2c5f83;font-size:16px;font-weight:900;padding:6px 0;}}QPushButton:hover{{background:{color2};}}")
        self.button_row.addWidget(self.start_btn)
        self.button_row.addWidget(self.pause_btn)
        self.button_row.addWidget(self.reset_btn)

        self.left_layout.addWidget(self.hero_card, 7)
        self.left_layout.addWidget(self.task_card, 1)
        self.left_layout.addLayout(self.duration_row)
        self.left_layout.addLayout(self.button_row)

        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d9e7f3;border-radius:22px;}")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(14, 12, 14, 12)
        self.right_layout.setSpacing(8)

        history_title = QLabel("今日记录")
        history_title.setStyleSheet("color:#2e5f84;font-size:20px;font-weight:900;")
        self.summary_label = QLabel("默认记录已加载")
        self.summary_label.setStyleSheet("background:#f7fbff;border:1px solid #d9e7f3;border-radius:14px;color:#4e6f88;font-size:13px;font-weight:800;padding:10px;")
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("QListWidget{background:#fffdfb;border:1px solid #f1e6da;border-radius:16px;padding:6px;font-size:12px;}QListWidget::item{border:0px;padding:4px 0;}")
        self.history_list.itemPressed.connect(self._on_history_item_pressed)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        self.history_long_press_candidate = False
        self.history_press_timer = QTimer(self)
        self.history_press_timer.setSingleShot(True)
        self.history_press_timer.timeout.connect(self._show_chart_dialog)

        self.right_layout.addWidget(history_title)
        self.right_layout.addWidget(self.summary_label)
        self.right_layout.addWidget(self.history_list, 1)

        self.root_layout.addWidget(self.left_shell, 11)
        self.root_layout.addWidget(self.right_panel, 9)

        self.start_btn.clicked.connect(self._start_timer)
        self.pause_btn.clicked.connect(self._pause_timer)
        self.reset_btn.clicked.connect(self._reset_timer)
        self.focus_spin.valueChanged.connect(self._on_duration_changed)
        self.break_spin.valueChanged.connect(self._on_duration_changed)
        self._apply_compact_layout()

    def _duration_card(self, title: str, widget: QWidget) -> QWidget:
        card = QFrame()
        card.setMinimumHeight(76)
        card.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d9e7f3;border-radius:16px;}")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setStyleSheet("color:#6d8ba0;font-size:12px;font-weight:800;")
        widget.setMinimumHeight(34)
        layout.addWidget(label)
        layout.addWidget(widget)
        return card

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_compact_layout()

    def _apply_compact_layout(self):
        compact = self.height() <= 410 or self.width() <= 760
        self.root_layout.setSpacing(8 if compact else 10)
        self.left_layout.setContentsMargins(10 if compact else 14, 10 if compact else 14, 10 if compact else 14, 10 if compact else 14)
        self.left_layout.setSpacing(8 if compact else 10)
        self.hero_layout.setContentsMargins(14 if compact else 18, 14 if compact else 18, 14 if compact else 18, 12 if compact else 16)
        self.timer_label.setStyleSheet(f"background:transparent;color:#2f77a8;font-size:{48 if compact else 60}px;font-weight:900;")
        self.status_chip.setStyleSheet("background:#ffffff;border:1px solid #d7e7f3;border-radius:15px;color:#4e6f88;font-size:13px;font-weight:800;padding:6px 18px;")
        self.task_edit.setMinimumHeight(30 if compact else 36)
        for card in (self.focus_card, self.break_card):
            card.setMinimumHeight(70 if compact else 78)
            card.setMaximumHeight(70 if compact else 78)
        for spin in (self.focus_spin, self.break_spin):
            spin.setMinimumHeight(30 if compact else 34)
        for btn in (self.start_btn, self.pause_btn, self.reset_btn):
            btn.setMinimumHeight(38 if compact else 46)
            btn.setMaximumHeight(38 if compact else 46)

    def _default_history_items(self) -> list[dict]:
        return [{"kind": "default", "task": name, "hours": hours} for name, hours in DEFAULT_RECORDS]

    def _load_state(self):
        self.history = []
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.focus_minutes = int(data.get("focus_minutes", 25) or 25)
        self.break_minutes = int(data.get("break_minutes", 5) or 5)
        self.remaining_seconds = int(data.get("remaining_seconds", self.focus_minutes * 60) or self.focus_minutes * 60)
        self.is_focus_mode = bool(data.get("is_focus_mode", True))
        self.task_edit.setText(str(data.get("current_task", "") or ""))
        self.focus_spin.setValue(self.focus_minutes)
        self.break_spin.setValue(self.break_minutes)
        custom = data.get("history", [])
        if isinstance(custom, list):
            for item in custom:
                if not isinstance(item, dict):
                    continue
                task = str(item.get("task", "")).strip()
                if not task or task == "暂无":
                    continue
                hours = float(item.get("hours", 0) or 0)
                if hours <= 0:
                    continue
                self.history.append({"kind": "custom", "mode": item.get("mode", "focus"), "task": task, "hours": hours, "completed_at": item.get("completed_at", "")})

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "focus_minutes": self.focus_minutes,
            "break_minutes": self.break_minutes,
            "remaining_seconds": self.remaining_seconds,
            "is_focus_mode": self.is_focus_mode,
            "current_task": self.task_edit.text().strip(),
            "history": [item for item in self.history if item.get("kind") == "custom"],
        }
        self.state_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _format_time(self) -> str:
        mins, secs = divmod(max(0, self.remaining_seconds), 60)
        return f"{mins:02d}:{secs:02d}"

    def _refresh_ui(self):
        self.timer_label.setText(self._format_time())
        if self.is_running:
            self.status_chip.setText("状态：进行中")
        elif self.remaining_seconds > 0:
            self.status_chip.setText("状态：待开始")
        else:
            self.status_chip.setText("状态：已完成")

        self.history_list.clear()
        self.history_list.addItem(QListWidgetItem("今日记录"))
        for name, hours in DEFAULT_RECORDS:
            self.history_list.addItem(QListWidgetItem(name))
        if self.history:
            self.history_list.addItem(QListWidgetItem("新增记录"))
            for item in reversed(self.history[-20:]):
                task = str(item.get("task", "")).strip()
                if not task:
                    continue
                self.history_list.addItem(QListWidgetItem(task))
        self.summary_label.setText(f"已完成专注：{sum(1 for item in self.history if item.get('mode') == 'focus')} 次")
        self._save_state()

    def _on_duration_changed(self):
        self.focus_minutes = self.focus_spin.value()
        self.break_minutes = self.break_spin.value()
        if not self.is_running:
            self.remaining_seconds = (self.focus_minutes if self.is_focus_mode else self.break_minutes) * 60
        self._refresh_ui()

    def _start_timer(self):
        self.is_running = True
        self._refresh_ui()

    def _pause_timer(self):
        self.is_running = False
        self._refresh_ui()

    def _reset_timer(self):
        self.is_running = False
        self.remaining_seconds = (self.focus_minutes if self.is_focus_mode else self.break_minutes) * 60
        self._refresh_ui()

    def trigger_voice_action(self, action: str, payload: dict | None = None) -> bool:
        action = str(action or "").strip()
        payload = payload or {}
        if action == "start_pomodoro":
            task = str(payload.get("task", "") or "").strip()
            focus_minutes = str(payload.get("focus_minutes", "") or "").strip()
            if task:
                self.task_edit.setText(task)
            if focus_minutes.isdigit():
                minutes = max(1, min(120, int(focus_minutes)))
                self.focus_spin.setValue(minutes)
                self.focus_minutes = minutes
                self.remaining_seconds = minutes * 60
            self._start_timer()
            return True
        if action == "pause_pomodoro":
            self._pause_timer()
            return True
        if action == "reset_pomodoro":
            self._reset_timer()
            return True
        return False

    def _switch_mode(self):
        self.is_focus_mode = not self.is_focus_mode
        self.is_running = False
        self.remaining_seconds = (self.focus_minutes if self.is_focus_mode else self.break_minutes) * 60
        self._refresh_ui()

    def _append_history(self):
        task_name = self.task_edit.text().strip()
        if task_name and task_name != "暂无":
            self.history.append(
                {
                    "kind": "custom",
                    "mode": "focus" if self.is_focus_mode else "break",
                    "task": task_name,
                    "hours": round(self.focus_minutes / 60.0 if self.is_focus_mode else self.break_minutes / 60.0, 2),
                    "completed_at": datetime.now().strftime("%H:%M"),
                }
            )

    def _tick(self):
        if not self.is_running:
            return
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self.is_running = False
            self._append_history()
            self._refresh_ui()
            self._switch_mode()
            return
        self._refresh_ui()

    def _on_history_item_pressed(self, item: QListWidgetItem):
        if item.text() == "今日记录":
            self.history_long_press_candidate = True
            self.history_press_timer.start(650)
        else:
            self.history_long_press_candidate = False

    def _on_history_item_clicked(self, item: QListWidgetItem):
        if item.text() == "今日记录":
            self._show_chart_dialog()

    def _show_chart_dialog(self):
        self.history_long_press_candidate = False
        records = [{"name": name, "hours": hours} for name, hours in DEFAULT_RECORDS]
        for item in self.history:
            task = str(item.get("task", "")).strip()
            hours = float(item.get("hours", 0) or 0)
            if task and hours > 0:
                records.append({"name": task, "hours": hours})
        FocusChartDialog(records, self).exec_()
