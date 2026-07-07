from __future__ import annotations

import time
from collections import deque
from pathlib import Path

import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

from app.interfaces.onnx_pose_runtime import PoseDetector, draw_pose


CN_FONT = '"Noto Sans CJK SC", "Microsoft YaHei", "WenQuanYi Micro Hei"'


class WorkoutScoring:
    TASKS = [
        {"exercise": "raise", "reps": 5, "weight": 20.0},
        {"exercise": "jumping_jack", "reps": 5, "weight": 10.0},
        {"exercise": "squat", "reps": 10, "weight": 40.0},
        {"exercise": "lunge", "reps": 20, "weight": 20.0},
    ]

    def __init__(self):
        self.current_task = 0
        self.current_reps = 0
        self.score = 0.0

    def get_current_task(self) -> str:
        if self.current_task >= len(self.TASKS):
            return "Finished"
        return self.TASKS[self.current_task]["exercise"]


class ScoreHistoryChart(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points = []
        self.setMinimumHeight(180)

    def set_points(self, points):
        self.points = list(points or [])
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#FBFDFF"))
        rect = self.rect().adjusted(24, 18, -24, -30)
        painter.setPen(QtGui.QPen(QtGui.QColor(231, 237, 243), 1))
        for i in range(5):
            y = rect.top() + i * rect.height() / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))
        if not self.points:
            painter.setPen(QtGui.QColor("#8EA4B6"))
            painter.setFont(QtGui.QFont("Microsoft YaHei", 11, QtGui.QFont.DemiBold))
            painter.drawText(rect, QtCore.Qt.AlignCenter, "完成更多训练后，这里会显示成绩变化")
            return


class SwipePage(QtWidgets.QWidget):
    def __init__(self, on_left_swipe=None, on_right_swipe=None, parent=None):
        super().__init__(parent)
        self.on_left_swipe = on_left_swipe
        self.on_right_swipe = on_right_swipe
        self._press_pos = None
        self.setStyleSheet("background:#f4f8fc;")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._press_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._press_pos is not None:
            delta = event.pos() - self._press_pos
            if abs(delta.x()) > 48 and abs(delta.x()) > abs(delta.y()):
                if delta.x() < 0 and self.on_left_swipe:
                    self.on_left_swipe()
                elif delta.x() > 0 and self.on_right_swipe:
                    self.on_right_swipe()
        self._press_pos = None
        super().mouseReleaseEvent(event)


class PoseWindow(QtWidgets.QMainWindow):
    EXERCISE_DEFS = [
        ("raise", "手臂上举", "上肢舒展训练"),
        ("jumping_jack", "开合跳", "全身热身动作"),
        ("squat", "深蹲", "强化腿部力量"),
        ("lunge", "弓步蹲", "训练核心与平衡"),
    ]

    def __init__(self, model_path: str, camera_index: int, width: int, height: int):
        super().__init__()
        self.setWindowTitle("RDK X5 YOLOv8 Pose")
        self.resize(width, height)
        self.model_path = model_path
        self.camera_index = camera_index
        self.camera_width = width
        self.camera_height = height
        self.project_root = Path(__file__).resolve().parent
        self.history_file = self.project_root / "fitness_score_history.json"
        self.scoring = WorkoutScoring()
        self.detector = None
        self.cap = None
        self.prev_time = time.time()
        self.active_exercise = self.scoring.get_current_task()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.entry_stack = QtWidgets.QStackedWidget()
        self.home_page = self._build_home_page()
        self.exercise_page = self._build_exercise_page()
        self.video_label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.video_label.setStyleSheet("background:#081b2a;border:none;border-radius:20px;color:white;")
        self.video_label.setText("健身界面加载中")
        self.entry_stack.addWidget(self.home_page)
        self.entry_stack.addWidget(self.exercise_page)
        self.entry_stack.addWidget(self.video_label)
        self.setCentralWidget(self.entry_stack)

    def _build_home_page(self):
        page = SwipePage(on_left_swipe=self._show_exercise_page)
        layout = QtWidgets.QVBoxLayout(page)
        layout.addStretch(1)
        title = QtWidgets.QLabel("健身模式")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color:#183B59;font-size:28px;font-weight:900;")
        subtitle = QtWidgets.QLabel("左滑开始训练")
        subtitle.setAlignment(QtCore.Qt.AlignCenter)
        subtitle.setStyleSheet("color:#5f7891;font-size:16px;font-weight:700;")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addStretch(1)
        return page

    def _build_exercise_page(self):
        page = SwipePage(on_right_swipe=self._show_home_page)
        layout = QtWidgets.QVBoxLayout(page)
        layout.addWidget(QtWidgets.QLabel("训练中"))
        return page

    def _show_home_page(self):
        self.entry_stack.setCurrentWidget(self.home_page)

    def _show_exercise_page(self):
        self.entry_stack.setCurrentWidget(self.exercise_page)
        self.start_camera()

    def on_page_shown(self):
        self.start_camera()

    def on_page_hidden(self):
        self.stop_camera()

    def start_camera(self):
        if self.detector is None:
            self.detector = PoseDetector(self.model_path)
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
        if self.cap is not None and self.cap.isOpened() and not self.timer.isActive():
            self.prev_time = time.time()
            self.timer.start(30)

    def stop_camera(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def update_frame(self):
        if self.cap is None or self.detector is None:
            return
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return
        input_tensor, scale, pad_x, pad_y = self.detector.preprocess(frame)
        try:
            output = self.detector.forward(input_tensor)
            poses = self.detector.postprocess(output, frame.shape, scale, pad_x, pad_y)
        except Exception:
            poses = []
        draw_pose(frame, poses)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(image).scaled(self.video_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))


class FitnessPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        self.window = PoseWindow(str(Path(__file__).resolve().parent / "yolov8n_pose_bayese_416x416_nv12.bin"), 0, 844, 540)
        layout.addWidget(self.window)

    def on_page_shown(self):
        self.window.on_page_shown()

    def on_page_hidden(self):
        self.window.on_page_hidden()

    def trigger_voice_action(self, action: str, payload: dict | None = None) -> bool:
        if action in {"start_workout", "start_rehab_training"}:
            self.on_page_shown()
            return True
        return False

