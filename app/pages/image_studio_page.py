from __future__ import annotations

import json
import pathlib
from datetime import datetime

from PyQt5.QtCore import QPoint, QObject, QRunnable, Qt, QThreadPool, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.interfaces.edge_gateway import EdgeGatewayClient
from app.workers import JsonWorker


class WorkerSignals(QObject):
    success = pyqtSignal(bytes)
    error = pyqtSignal(str)


class BytesWorker(QRunnable):
    def __init__(self, run_fn):
        super().__init__()
        self.run_fn = run_fn
        self.signals = WorkerSignals()

    def run(self):
        try:
            self.signals.success.emit(self.run_fn())
        except Exception as exc:
            self.signals.error.emit(str(exc))


class PaintableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.base_pixmap = None
        self.draw_layer = None
        self.scale_factor = 1.0
        self.pen_color = QColor("#2f8fe9")
        self.pen_width = 6
        self._drawing = False
        self._last_point = QPoint()

    def set_base_pixmap(self, pixmap: QPixmap):
        self.base_pixmap = pixmap.copy()
        self.draw_layer = QPixmap(self.base_pixmap.size())
        self.draw_layer.fill(Qt.transparent)
        self._render()

    def get_composited_pixmap(self) -> QPixmap:
        if not self.base_pixmap:
            return QPixmap()
        composed = self.base_pixmap.copy()
        painter = QPainter(composed)
        if self.draw_layer:
            painter.drawPixmap(0, 0, self.draw_layer)
        painter.end()
        return composed

    def set_scale_factor(self, scale_factor: float):
        self.scale_factor = max(0.1, min(scale_factor, 8.0))
        self._render()

    def set_pen_color(self, color: QColor):
        if color.isValid():
            self.pen_color = color

    def set_pen_width(self, width: int):
        self.pen_width = max(1, int(width))

    def clear_drawing(self):
        if self.draw_layer:
            self.draw_layer.fill(Qt.transparent)
            self._render()

    def _render(self):
        if not self.base_pixmap:
            self.setText("暂无图片")
            self.setPixmap(QPixmap())
            return
        composed = self.get_composited_pixmap()
        w = max(1, int(self.base_pixmap.width() * self.scale_factor))
        h = max(1, int(self.base_pixmap.height() * self.scale_factor))
        scaled = composed.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled)
        self.resize(scaled.size())

    def _to_base_point(self, pos: QPoint) -> QPoint:
        if not self.base_pixmap or self.width() <= 0 or self.height() <= 0:
            return QPoint(0, 0)
        x = int(pos.x() * self.base_pixmap.width() / max(1, self.width()))
        y = int(pos.y() * self.base_pixmap.height() / max(1, self.height()))
        x = max(0, min(self.base_pixmap.width() - 1, x))
        y = max(0, min(self.base_pixmap.height() - 1, y))
        return QPoint(x, y)

    def _draw_line(self, p1: QPoint, p2: QPoint):
        if not self.draw_layer:
            return
        painter = QPainter(self.draw_layer)
        pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(p1, p2)
        painter.end()
        self._render()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.base_pixmap:
            self._drawing = True
            self._last_point = self._to_base_point(event.pos())
            self._draw_line(self._last_point, self._last_point)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drawing and (event.buttons() & Qt.LeftButton):
            point = self._to_base_point(event.pos())
            self._draw_line(self._last_point, point)
            self._last_point = point
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drawing = False
        super().mouseReleaseEvent(event)


class ImageZoomDialog(QDialog):
    image_updated = pyqtSignal(QPixmap)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("图片查看与绘制")
        self.resize(1000, 720)
        self.scale_factor = 1.0
        self.base_pixmap = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        btn_row = QHBoxLayout()
        self.zoom_out_btn = QPushButton("-")
        self.zoom_in_btn = QPushButton("+")
        self.reset_btn = QPushButton("重置")
        self.fit_btn = QPushButton("适应窗口")
        self.color_btn = QPushButton("画笔颜色")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(1, 60)
        self.width_spin.setValue(6)
        self.clear_btn = QPushButton("清除涂鸦")
        self.apply_btn = QPushButton("应用")
        self.save_btn = QPushButton("另存为")
        for widget in (self.zoom_out_btn, self.zoom_in_btn, self.reset_btn, self.fit_btn, self.color_btn, self.clear_btn, self.apply_btn, self.save_btn):
            btn_row.addWidget(widget)
        btn_row.addWidget(QLabel("画笔:"))
        btn_row.addWidget(self.width_spin)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.image_label = PaintableImageLabel()
        self.image_label.setText("暂无图片")
        self.scroll = QScrollArea()
        self.scroll.setWidget(self.image_label)
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scroll, 1)

        self.zoom_out_btn.clicked.connect(self.zoom_out)
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        self.reset_btn.clicked.connect(self.reset_zoom)
        self.fit_btn.clicked.connect(self.fit_to_window)
        self.color_btn.clicked.connect(self.pick_color)
        self.width_spin.valueChanged.connect(self.on_width_changed)
        self.clear_btn.clicked.connect(self.clear_drawing)
        self.apply_btn.clicked.connect(self.apply_changes)
        self.save_btn.clicked.connect(self.save_as)

    def set_pixmap(self, pixmap: QPixmap):
        self.base_pixmap = pixmap
        self.scale_factor = 1.0
        self.image_label.set_base_pixmap(pixmap)
        self.fit_to_window()

    def _render(self):
        self.image_label.set_scale_factor(self.scale_factor)

    def zoom_in(self):
        self.scale_factor = min(self.scale_factor * 1.25, 8.0)
        self._render()

    def zoom_out(self):
        self.scale_factor = max(self.scale_factor / 1.25, 0.1)
        self._render()

    def reset_zoom(self):
        self.scale_factor = 1.0
        self._render()

    def fit_to_window(self):
        if not self.base_pixmap or self.base_pixmap.isNull():
            return
        vw = max(1, self.scroll.viewport().width() - 8)
        vh = max(1, self.scroll.viewport().height() - 8)
        pw = max(1, self.base_pixmap.width())
        ph = max(1, self.base_pixmap.height())
        self.scale_factor = min(vw / pw, vh / ph)
        self.scale_factor = min(max(self.scale_factor, 0.1), 8.0)
        self._render()

    def pick_color(self):
        color = QColorDialog.getColor(self.image_label.pen_color, self, "选择画笔颜色")
        if color.isValid():
            self.image_label.set_pen_color(color)

    def on_width_changed(self, value: int):
        self.image_label.set_pen_width(value)

    def clear_drawing(self):
        self.image_label.clear_drawing()

    def apply_changes(self):
        pixmap = self.image_label.get_composited_pixmap()
        if pixmap and not pixmap.isNull():
            self.image_updated.emit(pixmap)

    def save_as(self):
        pixmap = self.image_label.get_composited_pixmap()
        if not pixmap or pixmap.isNull():
            QMessageBox.warning(self, "提示", "没有可保存的图片。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存图片", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;WEBP (*.webp)")
        if path and not pixmap.save(path):
            QMessageBox.critical(self, "错误", f"保存失败：{path}")


class ImageStudioPage(QWidget):
    def __init__(self, client: EdgeGatewayClient | None = None):
        super().__init__()
        self.client = client or EdgeGatewayClient()
        self.pool = QThreadPool.globalInstance()
        self.generated_dir = pathlib.Path(__file__).resolve().parents[2] / "output" / "generated_images"
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.debug_log_path = pathlib.Path(__file__).resolve().parents[2] / "output" / "image_studio.log"
        self.history: list[dict] = []
        self.current_pixmap = QPixmap()
        self.zoom_dialog = ImageZoomDialog(self)
        self.zoom_dialog.image_updated.connect(self._apply_zoom_update)
        self._build_ui()
        self._load_existing_history()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("QFrame{background:#f4f9ff;border:1px solid #d7e6f5;border-radius:18px;}")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(14, 14, 14, 14)
        self.left_layout.setSpacing(8)

        self.prompt_label = QLabel("提示词")
        self.prompt_label.setStyleSheet("color:#2d5674;font-size:13px;font-weight:800;")
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("例如：浅蓝色简约风客厅中的白猫插画，柔和光线，干净背景")
        self.prompt_edit.setStyleSheet("QTextEdit{background:#ffffff;border:1px solid #d9e8f4;border-radius:14px;padding:8px;color:#21445f;font-size:13px;}")
        self.status_label = QLabel("状态：等待生成")
        self.status_label.setStyleSheet("color:#406e8d;font-size:13px;font-weight:700;")
        self.generate_btn = QPushButton("生成图片")
        self.generate_btn.setStyleSheet("QPushButton{background:#67c7ff;border:1px solid #3aa2dc;border-radius:16px;color:#ffffff;font-size:16px;font-weight:800;padding:12px 0;}QPushButton:hover{background:#57baf0;}QPushButton:disabled{background:#b8dff7;border-color:#9cc9e6;color:#edf7ff;}")
        self.history_label = QLabel("生成历史")
        self.history_label.setStyleSheet("color:#2d5674;font-size:13px;font-weight:800;")
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("QListWidget{background:#ffffff;border:1px solid #d9e8f4;border-radius:16px;padding:6px;color:#21445f;}QListWidget::item{padding:8px 6px;border-radius:10px;}QListWidget::item:selected{background:#dff0ff;color:#173952;}")
        self.output_label = QLabel("接口输出")
        self.output_label.setStyleSheet("color:#2d5674;font-size:13px;font-weight:800;")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("QTextEdit{background:#ffffff;border:1px solid #d9e8f4;border-radius:14px;padding:8px;color:#21445f;font-size:12px;}")
        self.left_layout.addWidget(self.prompt_label)
        self.left_layout.addWidget(self.prompt_edit)
        self.left_layout.addWidget(self.status_label)
        self.left_layout.addWidget(self.generate_btn)
        self.left_layout.addWidget(self.history_label)
        self.left_layout.addWidget(self.history_list, 1)
        self.left_layout.addWidget(self.output_label)
        self.left_layout.addWidget(self.output, 1)

        self.preview_panel = QFrame()
        self.preview_panel.setStyleSheet("QFrame{background:#ffffff;border:1px solid #d9e8f4;border-radius:18px;}")
        self.center_layout = QVBoxLayout(self.preview_panel)
        self.center_layout.setContentsMargins(14, 14, 14, 14)
        self.center_layout.setSpacing(8)
        center_title = QLabel("图片预览")
        center_title.setStyleSheet("color:#1e4a68;font-size:20px;font-weight:900;")
        self.preview = QLabel("生成后的图片会显示在这里")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview.setStyleSheet("QLabel{background:#f8fbff;border:1px dashed #bfd7ec;border-radius:18px;color:#6d8599;font-size:14px;font-weight:600;}")
        self.center_layout.addWidget(center_title)
        self.center_layout.addWidget(self.preview, 1)

        self.tools_panel = QFrame()
        self.tools_panel.setStyleSheet("QFrame{background:#f4f9ff;border:1px solid #d7e6f5;border-radius:18px;}")
        self.right_layout = QVBoxLayout(self.tools_panel)
        self.right_layout.setContentsMargins(14, 14, 14, 14)
        self.right_layout.setSpacing(8)
        right_title = QLabel("绘图工具")
        right_title.setStyleSheet("color:#1e4a68;font-size:20px;font-weight:900;")
        secondary_style = "QPushButton{background:#ffffff;border:1px solid #bad4ea;border-radius:14px;color:#28648d;font-size:15px;font-weight:800;padding:12px 0;}QPushButton:hover{background:#eef7ff;}"
        self.open_painter_btn = QPushButton("打开画板")
        self.open_painter_btn.setStyleSheet(secondary_style)
        self.save_btn = QPushButton("保存当前图")
        self.save_btn.setStyleSheet(secondary_style)
        self.right_layout.addWidget(right_title)
        self.right_layout.addWidget(self.open_painter_btn)
        self.right_layout.addWidget(self.save_btn)
        self.right_layout.addStretch(1)

        right_column = QWidget()
        right_column_layout = QVBoxLayout(right_column)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        right_column_layout.setSpacing(10)
        right_column_layout.addWidget(self.preview_panel, 7)
        right_column_layout.addWidget(self.tools_panel, 4)

        root.addWidget(self.left_panel, 5)
        root.addWidget(right_column, 9)

        self.generate_btn.clicked.connect(self.generate)
        self.open_painter_btn.clicked.connect(self.open_painter)
        self.save_btn.clicked.connect(self.save_current_image)
        self.history_list.itemClicked.connect(self._load_history_item)

    def _load_existing_history(self):
        for path in sorted(self.generated_dir.glob("*.png"), reverse=True):
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, str(path))
            self.history_list.addItem(item)

    def _append_history(self, prompt: str, payload: dict, image_path: str | None = None):
        row = {"prompt": prompt, "payload": payload, "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "image_path": image_path or ""}
        self.history.insert(0, row)
        self.history_list.clear()
        for item in self.history[:20]:
            self.history_list.addItem(QListWidgetItem(f"{item['created_at']}  {item['prompt']}"))

    def _format_output(self, obj) -> str:
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, dict):
            for key in ("image_path", "path", "reply_text", "text", "content", "result"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(data)

    def _flux_client(self) -> EdgeGatewayClient:
        return self.client

    def _append_debug_log(self, message: str):
        try:
            self.debug_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.debug_log_path.open("a", encoding="utf-8") as fp:
                fp.write(f"{datetime.now().isoformat()} {message}\n")
        except Exception:
            pass

    def _set_preview_pixmap(self, pixmap: QPixmap):
        self.current_pixmap = pixmap
        if pixmap.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("预览失败")
            return
        scaled = pixmap.scaled(max(220, self.preview.width() - 18), max(170, self.preview.height() - 18), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(scaled)
        self.preview.setText("")

    def generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "提示", "请先输入提示词。")
            return
        self.generate_btn.setEnabled(False)
        self.status_label.setText("状态：正在生成图片...")
        self._append_debug_log(f"generate start prompt={prompt[:80]}")

        worker = JsonWorker(lambda: self._flux_client().request_image_generation(prompt))
        worker.signals.success.connect(lambda obj: self._on_generate_success(prompt, obj))
        worker.signals.error.connect(self._on_generate_error)
        self.pool = QThreadPool.globalInstance()
        self.pool.start(worker)

    def _on_generate_success(self, prompt: str, obj):
        self.generate_btn.setEnabled(True)
        self.status_label.setText("状态：生成完成")
        self.output_text = self._format_output(obj)
        self.output.setPlainText(self.output_text)
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, dict):
            path = data.get("image_path") or data.get("path")
            if path:
                pixmap = QPixmap(str(path))
                self._set_preview_pixmap(pixmap)
                self._append_history(prompt, data, image_path=str(path))
                return
            self._append_history(prompt, data)
            if "image" in data and isinstance(data["image"], str):
                self.output_text = str(data["image"])
        elif isinstance(data, str):
            self.output_text = data
        self._append_debug_log("generate success")

    def _on_generate_error(self, message: str):
        self.generate_btn.setEnabled(True)
        self.status_label.setText("状态：生成失败")
        QMessageBox.warning(self, "生成失败", message)
        self._append_debug_log(f"generate error {message}")

    def _load_history_item(self, item: QListWidgetItem):
        idx = self.history_list.row(item)
        if idx < 0 or idx >= len(self.history):
            path = pathlib.Path(str(item.data(Qt.UserRole)))
            if path.exists():
                self._set_preview_pixmap(QPixmap(str(path)))
                self.status_label.setText(f"状态：已加载 {path.name}")
            return
        row = self.history[idx]
        self.prompt_edit.setPlainText(str(row.get("prompt", "")))
        self.output.setPlainText(json.dumps(row.get("payload", {}), ensure_ascii=False, indent=2))
        payload = row.get("payload", {})
        self._append_debug_log(f"load history prompt={row.get('prompt', '')}")
        path = row.get("image_path")
        if path and pathlib.Path(path).exists():
            self._set_preview_pixmap(QPixmap(str(path)))
            self.status_label.setText(f"状态：已加载 {pathlib.Path(path).name}")
        else:
            QMessageBox.information(self, "历史记录", json.dumps(payload, ensure_ascii=False, indent=2))

    def _apply_zoom_update(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self._set_preview_pixmap(pixmap)
            self.status_label.setText("状态：已应用绘图修改")

    def open_painter(self):
        if self.current_pixmap.isNull():
            QMessageBox.information(self, "提示", "请先生成或加载一张图片。")
            return
        self.zoom_dialog.set_pixmap(self.current_pixmap)
        self.zoom_dialog.exec_()

    def save_current_image(self):
        if self.current_pixmap.isNull():
            QMessageBox.information(self, "提示", "当前没有图片可保存。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存当前图片", "", "PNG (*.png);;JPEG (*.jpg *.jpeg);;WEBP (*.webp)")
        if path and not self.current_pixmap.save(path):
            QMessageBox.warning(self, "提示", f"保存失败：{path}")
