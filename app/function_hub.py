from __future__ import annotations

import json
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QVBoxLayout, QWidget

from app.config import CONFIG
from app.pages import (
    FitnessPage,
    HomeworkPage,
    ImageStudioPage,
    LearningPage,
    PlaceholderPage,
    PomodoroPage,
    ReminderPage,
    SecurityInspectionPage,
    SittingPosturePage,
    StudentClockinPage,
    VideoPage,
    WeatherPage,
)


PAGE_TITLES = {
    "weather": "天气页面",
    "reminder": "提醒日记",
    "general_learning": "通识学习",
    "homework": "作业布置",
    "fitness": "健身模式",
    "sitting_posture": "坐姿检测",
    "video": "视频通话",
    "student_clockin": "学生打卡",
    "pomodoro": "专注模式",
    "image_studio": "生图绘画",
    "security_inspection": "安全巡检",
}

LIVE_TRANSCRIPT_DEFAULT = "等待唤醒：你好小智"


class FunctionHubWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RDK 功能中心")
        self.output_dir = CONFIG.output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.live_transcript_file = self.output_dir / "live_transcript.txt"
        self.page_command_file = self.output_dir / "page_command.json"
        self.page_cache: dict[str, QWidget] = {}
        self.current_widget: QWidget | None = None
        self._last_transcript = ""
        self._last_command_ts = 0.0
        self._build_ui()
        self._start_watchers()
        self.list_widget.setCurrentRow(0)

    def _build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        nav = QFrame()
        nav.setFixedWidth(220)
        nav_layout = QVBoxLayout(nav)
        self.list_widget = QListWidget()
        for key, title in PAGE_TITLES.items():
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, key)
            self.list_widget.addItem(item)
        self.list_widget.currentRowChanged.connect(self._on_nav_changed)
        self.transcript = QLabel(LIVE_TRANSCRIPT_DEFAULT)
        self.transcript.setWordWrap(True)
        self.transcript.setStyleSheet("background:#0f1f2b;color:#f4fbff;border-radius:14px;padding:10px;font-weight:700;")
        nav_layout.addWidget(QLabel("功能入口"))
        nav_layout.addWidget(self.list_widget, 1)
        nav_layout.addWidget(self.transcript)
        self.content = QFrame()
        self.content_layout = QVBoxLayout(self.content)
        self.placeholder = QLabel("请选择左侧页面")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(self.placeholder)
        layout.addWidget(nav)
        layout.addWidget(self.content, 1)
        self.setCentralWidget(root)

    def _start_watchers(self):
        self.transcript_timer = QTimer(self)
        self.transcript_timer.timeout.connect(self._poll_transcript)
        self.transcript_timer.start(200)
        self.command_timer = QTimer(self)
        self.command_timer.timeout.connect(self._poll_page_command)
        self.command_timer.start(200)

    def _poll_transcript(self):
        try:
            text = self.live_transcript_file.read_text(encoding="utf-8").strip()
        except Exception:
            text = ""
        if not text:
            text = LIVE_TRANSCRIPT_DEFAULT
        if text != self._last_transcript:
            self._last_transcript = text
            self.transcript.setText(text)

    def _poll_page_command(self):
        try:
            if not self.page_command_file.exists():
                return
            payload = json.loads(self.page_command_file.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, dict):
            return
        ts = float(payload.get("ts", 0.0) or 0.0)
        if ts <= self._last_command_ts:
            return
        self._last_command_ts = ts
        page = str(payload.get("page", "")).strip()
        if page and page in PAGE_TITLES:
            row = self._row_for_key(page)
            if row >= 0:
                self.list_widget.setCurrentRow(row)

    def _row_for_key(self, key: str) -> int:
        for idx in range(self.list_widget.count()):
            if self.list_widget.item(idx).data(Qt.UserRole) == key:
                return idx
        return -1

    def _page_for_key(self, key: str) -> QWidget:
        if key not in self.page_cache:
            if key == "weather":
                widget = WeatherPage()
            elif key == "reminder":
                widget = ReminderPage()
            elif key == "fitness":
                widget = FitnessPage()
            elif key == "sitting_posture":
                widget = SittingPosturePage()
            elif key == "general_learning":
                widget = LearningPage()
            elif key == "video":
                widget = VideoPage()
            elif key == "student_clockin":
                widget = StudentClockinPage()
            elif key == "pomodoro":
                widget = PomodoroPage()
            elif key == "image_studio":
                widget = ImageStudioPage()
            elif key == "homework":
                widget = HomeworkPage()
            elif key == "security_inspection":
                widget = SecurityInspectionPage()
            else:
                widget = PlaceholderPage(PAGE_TITLES[key], "该页面保留为接口占位模块，后续可按需接入。")
            self.page_cache[key] = widget
        return self.page_cache[key]

    def _show_page(self, key: str):
        if self.current_widget is not None:
            self.content_layout.removeWidget(self.current_widget)
            self.current_widget.hide()
        widget = self._page_for_key(key)
        self.content_layout.addWidget(widget)
        widget.show()
        self.current_widget = widget

    def _on_nav_changed(self, row: int):
        if row < 0:
            return
        key = self.list_widget.item(row).data(Qt.UserRole)
        self._show_page(key)


def main():
    app = QApplication([])
    win = FunctionHubWindow()
    win.resize(1280, 720)
    win.show()
    app.exec_()
