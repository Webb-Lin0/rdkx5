from __future__ import annotations

import math
import subprocess
import time
from pathlib import Path

import cv2
from PyQt5 import QtCore, QtGui, QtWidgets

from app.interfaces.onnx_pose_runtime import PoseDetector, draw_pose


CN_FONT = '"Noto Sans CJK SC", "Microsoft YaHei", "WenQuanYi Micro Hei"'


class SittingPosturePage(QtWidgets.QWidget):
    def __init__(
        self,
        model_path: str = "/home/sunrise/rdk_yolov8_pose/yolov8n_pose_bayese_416x416_nv12.bin",
        camera_index: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self.model_path = str(model_path)
        self.camera_index = camera_index
        self.detector = None
        self.cap = None
        self.prev_time = time.time()
        self.bad_frames = 0
        self.good_frames = 0
        self.sensitivity = 1.12
        self.last_alert_ts = 0.0
        self.audio_path = str(Path(__file__).resolve().parent / "keep_good_posture.wav")
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QHBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        self.setStyleSheet(
            f"""
            QWidget {{
                background:#f6fbff;
                color:#18324a;
                font-family:{CN_FONT};
            }}
            QFrame#panel {{
                background:#ffffff;
                border:1px solid #dce9f7;
                border-radius:18px;
            }}
            QLabel#title {{
                color:#1a4564;
                font-size:24px;
                font-weight:900;
            }}
            QLabel#status {{
                color:#1a4564;
                font-size:30px;
                font-weight:900;
            }}
            QLabel#detail {{
                color:#607f98;
                font-size:15px;
                font-weight:800;
            }}
            QLabel#metric {{
                color:#416178;
                font-size:16px;
                font-weight:900;
                line-height:1.45;
            }}
            """
        )

        self.video_label = QtWidgets.QLabel("坐姿检测摄像头准备中...", alignment=QtCore.Qt.AlignCenter)
        self.video_label.setMinimumSize(650, 500)
        self.video_label.setStyleSheet("background:#0b2235;border:none;border-radius:20px;color:white;font-size:18px;font-weight:800;")
        root.addWidget(self.video_label, 9)

        panel = QtWidgets.QFrame()
        panel.setObjectName("panel")
        panel_layout = QtWidgets.QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.setSpacing(8)

        title = QtWidgets.QLabel("坐姿检测")
        title.setObjectName("title")
        title.setAlignment(QtCore.Qt.AlignCenter)
        panel_layout.addWidget(title)

        self.status_label = QtWidgets.QLabel("等待检测")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(110)
        panel_layout.addWidget(self.status_label)

        self.detail_label = QtWidgets.QLabel("进入页面后自动开始检测")
        self.detail_label.setObjectName("detail")
        self.detail_label.setAlignment(QtCore.Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.setMinimumHeight(78)
        panel_layout.addWidget(self.detail_label)

        self.metric_label = QtWidgets.QLabel("距离比例: --\n连续异常: 0 帧\nFPS: --\n阈值: --")
        self.metric_label.setObjectName("metric")
        self.metric_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.metric_label.setStyleSheet("background:#eef7ff;border:1px solid #d5eaff;border-radius:16px;color:#416178;padding:14px;font-size:16px;font-weight:900;")
        panel_layout.addWidget(self.metric_label, 1)

        root.addWidget(panel, 3)

    def on_page_shown(self):
        self.start_camera()

    def on_page_hidden(self):
        self.stop_camera()

    def start_camera(self):
        if self.detector is None:
            self.detector = PoseDetector(self.model_path)
        if self.cap is None:
            self.cap = cv2.VideoCapture(self.camera_index)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 844)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
        if self.cap is not None and self.cap.isOpened() and not self.timer.isActive():
            self.prev_time = time.time()
            self.timer.start(30)
        elif self.cap is None or not self.cap.isOpened():
            self.status_label.setText("摄像头打开失败")
            self.detail_label.setText("请确认摄像头未被其他页面占用")

    def stop_camera(self):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    @staticmethod
    def _point(pose, idx: int, thres: float = 0.35):
        if pose is None or getattr(pose, "keypoints", None) is None or idx >= len(pose.keypoints):
            return None
        x, y, conf = pose.keypoints[idx]
        if conf < thres:
            return None
        return float(x), float(y)

    @staticmethod
    def _dist(a, b) -> float:
        if a is None or b is None:
            return 0.0
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _analyze_posture(self, pose):
        left_eye = self._point(pose, 1)
        right_eye = self._point(pose, 2)
        nose = self._point(pose, 0)
        left_shoulder = self._point(pose, 5)
        right_shoulder = self._point(pose, 6)
        left_elbow = self._point(pose, 7)
        right_elbow = self._point(pose, 8)
        shoulder_width = self._dist(left_shoulder, right_shoulder)
        head_points = [p for p in (left_eye, right_eye, nose) if p is not None]
        elbow_points = [p for p in (left_elbow, right_elbow) if p is not None]
        if shoulder_width <= 1.0 or not head_points or not elbow_points:
            return "unknown", 0.0, "请保持头部、肩膀和手肘进入画面"
        min_head_elbow = min(self._dist(h, e) for h in head_points for e in elbow_points)
        ratio = min_head_elbow / shoulder_width
        if ratio < self.sensitivity:
            return "bad", ratio, "请保持良好坐姿"
        return "good", ratio, "当前坐姿良好，请继续保持"

    def _play_alert_audio(self):
        now = time.time()
        if now - self.last_alert_ts < 4.0:
            return
        self.last_alert_ts = now
        if not Path(self.audio_path).exists():
            return
        try:
            subprocess.Popen(["aplay", "-q", self.audio_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

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
        pose = max(poses, key=lambda p: p.score) if poses else None
        state, ratio, detail = self._analyze_posture(pose)
        if state == "bad":
            self.bad_frames += 1
            self.good_frames = 0
        elif state == "good":
            self.good_frames += 1
            self.bad_frames = 0
        else:
            self.bad_frames = 0
            self.good_frames = 0
        now = time.time()
        fps = 1.0 / max(now - self.prev_time, 1e-6)
        self.prev_time = now
        if state == "bad" and self.bad_frames >= 5:
            status = "坐姿异常"
            color = (60, 110, 255)
            bg = "#fff3f3"
            self._play_alert_audio()
        elif state == "good" and self.good_frames >= 3:
            status = "坐姿良好"
            color = (120, 210, 80)
            bg = "#f0fff5"
        else:
            status = "检测中"
            color = (255, 190, 80)
            bg = "#fffaf0"
        self.status_label.setText(status)
        self.status_label.setStyleSheet(f"background:{bg};border:1px solid #dce9f7;border-radius:18px;padding:14px;color:#1a4564;font-size:30px;font-weight:900;font-family:{CN_FONT};")
        self.detail_label.setText(detail)
        self.metric_label.setText(f"距离比例: {ratio:.2f}\n连续异常: {self.bad_frames} 帧\nFPS: {fps:.1f}\n阈值: {self.sensitivity:.2f}")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QtGui.QImage(rgb.data, w, h, ch * w, QtGui.QImage.Format_RGB888)
        self.video_label.setPixmap(QtGui.QPixmap.fromImage(image).scaled(self.video_label.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

