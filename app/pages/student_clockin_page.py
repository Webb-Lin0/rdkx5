from __future__ import annotations

import json
import pathlib
import time
from datetime import datetime

import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from app.interfaces.student_clockin_onnx import StudentClockinONNXClient


EMOTION_LABELS = {
    "angry": "生气",
    "disgust": "厌恶",
    "fear": "害怕",
    "happy": "高兴",
    "sad": "难过",
    "surprise": "惊讶",
    "neutral": "平静",
    "pouty": "嘟嘴",
    "grimace": "鬼脸",
}

PLACEHOLDER_NAMES = ["小明", "小红", "小刚", "小丽", "小军", "小芳", "小杰", "小美", "小宇", "小雨"]


def sanitize_id(text: str, prefix: str) -> str:
    raw = (text or "").strip().lower()
    keep = "".join(ch if ("a" <= ch <= "z") or ("0" <= ch <= "9") else "_" for ch in raw)
    keep = "_".join([x for x in keep.split("_") if x])
    suffix = keep[:40] if keep else "user"
    return f"{prefix}_{suffix}"[:64]


class StudentClockinPage(QWidget):
    def __init__(self):
        super().__init__()
        self.face_camera = None
        self.face_camera_index = -1
        self.face_current_frame = None
        self.face_users = []
        self.face_selected_user_id = ""
        self.generated_dir = pathlib.Path("/home/sunrise/output/face_clockin")
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.face_registry_path = self.generated_dir / "users.json"
        self.face_client = StudentClockinONNXClient()
        self.face_timer = QTimer(self)
        self.face_timer.timeout.connect(self.update_face_camera_frame)
        self._build_ui()
        self._load_face_registry()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        camera_panel = QFrame()
        camera_panel.setFixedWidth(250)
        camera_panel.setStyleSheet("background:#f7fbff;border:1px solid #cfe1f3;border-radius:18px;")
        camera_layout = QVBoxLayout(camera_panel)
        camera_layout.setContentsMargins(12, 12, 12, 12)
        camera_layout.setSpacing(8)
        camera_layout.addWidget(QLabel("摄像头预览"))
        self.face_camera_preview = QLabel("摄像头准备中")
        self.face_camera_preview.setAlignment(Qt.AlignCenter)
        self.face_camera_preview.setMinimumSize(220, 150)
        self.face_camera_preview.setMaximumHeight(170)
        self.face_camera_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.face_camera_preview.setStyleSheet("border:1px solid #9fc3df;border-radius:14px;background:#0f1c28;color:#e6edf3;")
        camera_layout.addWidget(self.face_camera_preview, 1)
        self.face_status_label = QLabel("状态：等待打卡")
        self.face_status_label.setWordWrap(True)
        self.face_result_label = QLabel("")
        self.face_result_label.hide()
        self.face_clockin_btn = QPushButton("立即打卡")
        self.face_clockin_btn.setFixedHeight(42)
        camera_layout.addWidget(self.face_status_label)
        camera_layout.addWidget(self.face_result_label)
        camera_layout.addWidget(self.face_clockin_btn)

        manage_panel = QFrame()
        manage_panel.setStyleSheet("background:#f7fbff;border:1px solid #cfe1f3;border-radius:18px;")
        manage_layout = QVBoxLayout(manage_panel)
        manage_layout.setContentsMargins(12, 12, 12, 12)
        manage_layout.setSpacing(8)
        manage_layout.addWidget(QLabel("人脸录入"))
        name_row = QHBoxLayout()
        self.face_name_edit = QLineEdit()
        self.face_name_edit.setPlaceholderText("输入姓名或身份")
        self.face_add_btn = QPushButton("录入人脸")
        name_row.addWidget(QLabel("姓名"))
        name_row.addWidget(self.face_name_edit, 1)
        name_row.addWidget(self.face_add_btn)
        manage_layout.addLayout(name_row)

        left_column = QVBoxLayout()
        left_column.setSpacing(10)
        left_column.addWidget(camera_panel)
        left_column.addWidget(manage_panel)
        left_column.addStretch(1)

        records_panel = QFrame()
        records_panel.setStyleSheet("background:#f9fcff;border:1px solid #cfe1f3;border-radius:20px;")
        records_layout = QVBoxLayout(records_panel)
        records_layout.setContentsMargins(14, 14, 14, 14)
        records_layout.setSpacing(10)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("打卡数据库"))
        title_row.addStretch(1)
        title_row.addWidget(QLabel("深蓝：已打卡  浅蓝：未打卡"))
        records_layout.addLayout(title_row)
        self.face_people_wrap = QWidget()
        self.face_people_layout = QGridLayout(self.face_people_wrap)
        records_layout.addWidget(self.face_people_wrap, 1)
        detail_panel = QFrame()
        detail_layout = QHBoxLayout(detail_panel)
        detail_text = QVBoxLayout()
        detail_text.addWidget(QLabel("打卡详情"))
        self.face_log = QTextEdit()
        self.face_log.setReadOnly(True)
        detail_text.addWidget(self.face_log, 1)
        self.face_log_image = QLabel("暂无照片")
        self.face_log_image.setAlignment(Qt.AlignCenter)
        self.face_log_image.setMinimumSize(150, 72)
        detail_layout.addLayout(detail_text, 1)
        detail_layout.addWidget(self.face_log_image)
        records_layout.addWidget(detail_panel)
        top_row.addLayout(left_column, 0)
        top_row.addWidget(records_panel, 1)
        root.addLayout(top_row, 1)
        self.face_add_btn.clicked.connect(self.add_face_from_camera)
        self.face_clockin_btn.clicked.connect(self.punch_in_face)

    def _set_pet_emotion(self, emotion_type: str, label: str = "", prob: float = 0.0, user_name: str = ""):
        display = label or EMOTION_LABELS.get((emotion_type or "neutral").strip().lower(), "平静")
        who = (user_name or "待识别").strip()
        self.face_status_label.setText(f"状态：{who} / {display}")
        if prob > 0:
            self.face_result_label.setText(f"情绪识别：{display}\n置信度：{prob:.3f}")

    def _load_face_registry(self):
        try:
            if self.face_registry_path.exists():
                data = json.loads(self.face_registry_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.face_users = data
        except Exception:
            self.face_users = []
        self._save_face_registry()
        self._refresh_face_users_view()

    def _save_face_registry(self):
        self.face_registry_path.write_text(json.dumps(self.face_users, ensure_ascii=False, indent=2), encoding="utf-8")

    def _refresh_face_users_view(self):
        while self.face_people_layout.count():
            item = self.face_people_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        display_users = list(self.face_users[:10])
        while len(display_users) < 10:
            idx = len(display_users)
            display_users.append({"name": PLACEHOLDER_NAMES[idx] if idx < len(PLACEHOLDER_NAMES) else f"学生{idx + 1}", "user_id": "", "punched": False, "last_clockin_at": "等待录入", "last_log": "尚未录入人脸。", "last_image": "", "placeholder": True})
        for idx, item in enumerate(display_users):
            name = item.get("name", "") or item.get("user_id", "") or "未命名"
            btn = QPushButton(name[:4], self.face_people_wrap)
            btn.setFixedSize(78, 78)
            btn.setCursor(Qt.PointingHandCursor if not item.get("placeholder") else Qt.ArrowCursor)
            btn.setEnabled(not bool(item.get("placeholder")))
            if item.get("user_id", ""):
                btn.clicked.connect(lambda _checked=False, uid=item.get("user_id", ""): self._show_face_user_log(uid))
            self.face_people_layout.addWidget(btn, idx // 5, idx % 5, Qt.AlignCenter)

    def _show_face_user_log(self, user_id: str):
        for item in self.face_users:
            if str(item.get("user_id", "")).strip() == str(user_id).strip():
                self.face_log.setPlainText(str(item.get("last_log", "")) or "该用户还没有打卡日志")
                image_path = str(item.get("last_image", "")).strip()
                if image_path and pathlib.Path(image_path).exists():
                    pix = QPixmap(image_path)
                    self.face_log_image.setPixmap(pix.scaled(max(120, self.face_log_image.width() - 12), max(100, self.face_log_image.height() - 12), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    self.face_log_image.setText("")
                else:
                    self.face_log_image.setText("暂无打卡照片")
                return

    def _update_face_user_state(self, user_id: str, **fields):
        target_id = (user_id or "").strip()
        for idx, item in enumerate(self.face_users):
            if str(item.get("user_id", "")).strip() != target_id:
                continue
            item.update(fields)
            self.face_users[idx] = item
            self._save_face_registry()
            self._refresh_face_users_view()
            return

    def _upsert_face_user(self, name: str, user_id: str):
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for idx, item in enumerate(self.face_users):
            if str(item.get("user_id", "")).strip() == user_id:
                item["name"] = name
                item["updated_at"] = now_text
                self.face_users.pop(idx)
                self.face_users.insert(0, item)
                self._save_face_registry()
                self._refresh_face_users_view()
                return
        self.face_users.insert(0, {"name": name, "user_id": user_id, "updated_at": now_text, "punched": False, "last_log": "", "last_clockin_at": "", "last_image": ""})
        self._save_face_registry()
        self._refresh_face_users_view()

    def _face_status(self, text: str):
        self.face_status_label.setText(f"状态：{text}")

    def _frame_to_pixmap(self, frame) -> QPixmap:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        return QPixmap.fromImage(image)

    def _set_face_preview(self, frame):
        pix = self._frame_to_pixmap(frame)
        w = max(100, self.face_camera_preview.width() - 12)
        h = max(100, self.face_camera_preview.height() - 12)
        self.face_camera_preview.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def start_face_camera(self):
        if self.face_camera is not None and self.face_camera.isOpened():
            if not self.face_timer.isActive():
                self.face_timer.start(50)
            self._face_status(f"摄像头已启动：/dev/video{self.face_camera_index}")
            return
        self.stop_face_camera()
        for index in (0, 1, 2, 3):
            cap = cv2.VideoCapture(index)
            if not cap or not cap.isOpened():
                if cap:
                    cap.release()
                continue
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.release()
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.face_camera = cap
            self.face_camera_index = index
            self.face_timer.start(50)
            self._face_status(f"摄像头已启动：/dev/video{index}")
            self.update_face_camera_frame()
            return
        self.face_camera = None
        self.face_camera_index = -1
        self.face_camera_preview.setText("摄像头打开失败")
        self._face_status("摄像头打开失败")

    def stop_face_camera(self):
        self.face_timer.stop()
        if self.face_camera is not None:
            try:
                self.face_camera.release()
            except Exception:
                pass
        self.face_camera = None
        self.face_camera_index = -1
        self.face_current_frame = None
        self.face_camera_preview.setPixmap(QPixmap())
        self.face_camera_preview.setText("摄像头已停止")

    def update_face_camera_frame(self):
        if self.face_camera is None or not self.face_camera.isOpened():
            return
        ok, frame = self.face_camera.read()
        if not ok or frame is None:
            self._face_status("读取摄像头画面失败")
            return
        self.face_current_frame = frame.copy()
        self._set_face_preview(frame)

    def _require_face_frame(self):
        if self.face_current_frame is None:
            self.start_face_camera()
            self.update_face_camera_frame()
        if self.face_current_frame is None:
            raise RuntimeError("当前无法获取摄像头画面。")
        return self.face_current_frame.copy()

    def _encode_frame_jpeg(self, frame) -> bytes:
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if not ok:
            raise RuntimeError("JPEG 编码失败。")
        return bytes(buf)

    def _store_face_snapshot(self, frame, prefix: str, name: str = "") -> pathlib.Path:
        safe_name = sanitize_id(name or prefix, prefix)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = self.generated_dir / f"{prefix}_{safe_name}_{ts}.jpg"
        cv2.imwrite(str(path), frame)
        return path

    def add_face_from_camera(self):
        name = self.face_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请先输入姓名或身份。")
            return
        try:
            frame = self._require_face_frame()
            image_bytes = self._encode_frame_jpeg(frame)
        except Exception as exc:
            QMessageBox.warning(self, "警告", str(exc))
            return
        self.face_add_btn.setEnabled(False)
        self._face_status("正在录入人脸...")
        user_id = sanitize_id(name, "face")
        try:
            _ = self.face_client.image_to_base64(image_bytes)
            self._face_status("人脸录入接口已预留")
            self._upsert_face_user(name, user_id)
            saved = self._store_face_snapshot(frame, "enroll", name)
            self._update_face_user_state(user_id, last_log=f"已录入：{name}\n用户编号：{user_id}\n截图：{saved.name}", last_image="")
            self.face_result_label.setText(f"已录入人脸：{name}\n用户编号：{user_id}")
        except Exception as exc:
            self._face_status(f"录入失败 {exc}")
        finally:
            self.face_add_btn.setEnabled(True)

    def punch_in_face(self):
        try:
            frame = self._require_face_frame()
            image_bytes = self._encode_frame_jpeg(frame)
        except Exception as exc:
            QMessageBox.warning(self, "警告", str(exc))
            return
        self.face_clockin_btn.setEnabled(False)
        self._face_status("正在进行打卡识别...")
        try:
            result = self.face_client.recognize_and_detect_emotion(image_bytes)
            score = float(result.get("score", 0.0) or 0.0)
            user_id = str(result.get("user_id", "")).strip()
            user_name = str(result.get("user_name", "")).strip() or user_id or "未知"
            emotion_type = str(result.get("emotion_type", "")).strip()
            emotion_label = EMOTION_LABELS.get(emotion_type, emotion_type or "未知")
            emotion_prob = float(result.get("emotion_prob", 0.0) or 0.0)
            saved = self._store_face_snapshot(frame, "clockin", user_name)
            detail_log = f"打卡结果\n匹配到：{user_name}\n分数：{score:.2f}\n情绪：{emotion_label}（{emotion_prob:.3f}）\n截图：{saved.name}"
            self.face_result_label.setText(f"打卡结果\n匹配到：{user_name}\n分数：{score:.2f}\n情绪：{emotion_label}（{emotion_prob:.3f}）")
            self._face_status("打卡完成")
            if user_id:
                self._update_face_user_state(user_id, punched=True, last_log=detail_log, last_clockin_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), last_image=str(saved))
            self._set_pet_emotion(emotion_type if emotion_type else "neutral", emotion_label, emotion_prob, user_name)
        except Exception as exc:
            self._face_status(f"打卡失败 {exc}")
            self._set_pet_emotion("sad", "难过", 0.0)
        finally:
            self.face_clockin_btn.setEnabled(True)

