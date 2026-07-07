from __future__ import annotations

import json
from datetime import datetime

from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.config import CONFIG
from app.interfaces.edge_gateway import EdgeGatewayClient
from app.workers import JsonWorker


class SecurityInspectionPage(QWidget):
    def __init__(self, client: EdgeGatewayClient | None = None):
        super().__init__()
        self.client = client or EdgeGatewayClient()
        self.pool = QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        card = QFrame()
        card.setStyleSheet("QFrame{background:#fff;border:1px solid #d7e7f3;border-radius:18px;}")
        layout = QVBoxLayout(card)
        self.title = QLabel("安全巡检")
        self.location = QLineEdit("工业中心二楼")
        self.location.setPlaceholderText("巡检地点")
        self.note = QLineEdit("")
        self.note.setPlaceholderText("巡检备注")
        self.trigger_btn = QPushButton("发起巡检")
        self.trigger_btn.clicked.connect(self.start_inspection)
        self.status = QLabel("等待发起巡检")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.title)
        layout.addWidget(self.location)
        layout.addWidget(self.note)
        layout.addWidget(self.trigger_btn)
        layout.addWidget(self.status)
        layout.addWidget(self.output, 1)
        root.addWidget(card, 1)

    def _build_request_payload(self) -> dict:
        return {
            "inspection_flag": True,
            "location": self.location.text().strip(),
            "note": self.note.text().strip(),
            "request_time": datetime.now().isoformat(timespec="seconds"),
            "source": "rdk_share",
        }

    def _normalize_request_response(self, obj):
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
        return data

    def _build_upload_payload(self, data) -> dict:
        report = data.get("report") if isinstance(data, dict) else None
        if not isinstance(report, dict):
            report = data if isinstance(data, dict) else {"raw": data}
        return {
            "report": report,
            "source": "rdk_share",
            "location": self.location.text().strip(),
            "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        }

    def start_inspection(self):
        payload = self._build_request_payload()
        self.status.setText("已发送巡检请求，等待边缘设备返回结果...")
        worker = JsonWorker(lambda: self.client.request_security_inspection(payload))
        worker.signals.success.connect(self._on_request_success)
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def _on_request_success(self, obj):
        data = self._normalize_request_response(obj)
        self.output.setPlainText(json.dumps(data, ensure_ascii=False, indent=2))
        upload_base = CONFIG.tailscale_upload_base.strip()
        if upload_base:
            upload_worker = JsonWorker(lambda: self.client.upload_security_report(self._build_upload_payload(data), upload_base))
            upload_worker.signals.success.connect(self._on_upload_success)
            upload_worker.signals.error.connect(self._on_upload_error)
            self.pool.start(upload_worker)
            self.status.setText("巡检结果已返回，正在上传到 Tailscale 地址...")
        else:
            self.status.setText("巡检结果已返回，未配置 Tailscale 上传地址")

    def _on_upload_success(self, obj):
        self.status.setText("巡检结果已上传到 Tailscale 地址")
        self.output.append("\n[UPLOAD] " + json.dumps(obj.get("data", obj), ensure_ascii=False))

    def _on_upload_error(self, message: str):
        self.status.setText("上传失败")
        self.output.append("\n[UPLOAD_ERROR] " + message)

    def _on_error(self, message: str):
        self.status.setText("巡检请求失败")
        self.output.setPlainText(message)

    def trigger_voice_action(self, action: str, payload: dict | None = None) -> bool:
        if action == "start_security_inspection":
            self.start_inspection()
            return True
        return False

