from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class VideoPage(QWidget):
    def __init__(self):
        super().__init__()
        self.contacts = {
            "family_001": {"id": "family_001", "name": "家人A", "device": "android", "online": True},
            "family_002": {"id": "family_002", "name": "家人B", "device": "android", "online": False},
            "family_003": {"id": "family_003", "name": "家人C", "device": "board", "online": True},
        }
        self.active_call_id = ""
        self.active_peer_id = ""
        self.pending_call_id = ""
        self._build_ui()
        self.refresh_contacts()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.stack = QStackedWidget()
        self.lobby_page = QFrame()
        self.call_page = QFrame()
        self._build_lobby()
        self._build_call_page()
        self.stack.addWidget(self.lobby_page)
        self.stack.addWidget(self.call_page)

        root.addWidget(self.stack, 1)
        self.stack.setCurrentWidget(self.lobby_page)

    def _build_lobby(self):
        self.lobby_page.setStyleSheet("background:#eaf4ff;")
        layout = QVBoxLayout(self.lobby_page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.title = QLabel("视频通话")
        self.title.setStyleSheet("color:#1f2937;font-size:22px;font-weight:800;")
        self.refresh_btn = QPushButton("刷新联系人")
        self.refresh_btn.clicked.connect(self.refresh_contacts)
        top_row.addWidget(self.title)
        top_row.addStretch(1)
        top_row.addWidget(self.refresh_btn)
        layout.addLayout(top_row)

        self.status = QLabel("状态：等待接入通话服务")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #ddf3ff, stop:1 #c8e9ff);"
            "border:1px solid #9dcaeb;border-radius:10px;padding:8px 10px;color:#1f4c67;font-weight:700;font-size:12px;"
        )
        layout.addWidget(self.status)

        self.call_target_edit = QLineEdit()
        self.call_target_edit.setPlaceholderText("输入联系人名称或 ID")
        self.call_target_edit.setStyleSheet(
            "QLineEdit{background:#ffffff;border:1px solid #b8d7f2;border-radius:10px;padding:8px 10px;color:#244964;font-weight:700;}"
        )
        layout.addWidget(self.call_target_edit)

        self.contacts_scroll = QListWidget()
        self.contacts_scroll.setStyleSheet(
            "QListWidget{background:transparent;border:none;}"
            "QListWidget::item{margin:0;padding:0;}"
        )
        layout.addWidget(self.contacts_scroll, 1)

        action_row = QHBoxLayout()
        self.call_btn = QPushButton("发起通话")
        self.call_btn.clicked.connect(self._call_selected)
        self.voice_btn = QPushButton("模拟语音呼叫")
        self.voice_btn.clicked.connect(self._call_from_input)
        action_row.addWidget(self.voice_btn)
        action_row.addWidget(self.call_btn)
        layout.addLayout(action_row)

        self.lobby_log = QTextEdit()
        self.lobby_log.setReadOnly(True)
        self.lobby_log.setPlaceholderText("这里会显示通话请求与状态变更")
        self.lobby_log.setStyleSheet(
            "QTextEdit{background:#f9fdff;border:1px solid #b9d9f4;border-radius:14px;color:#244964;font-size:13px;padding:8px;}"
        )
        layout.addWidget(self.lobby_log, 1)

    def _build_call_page(self):
        self.call_page.setStyleSheet("background:#eaf4ff;")
        layout = QVBoxLayout(self.call_page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self.call_info = QLabel("通话中")
        self.call_info.setStyleSheet("color:#1f2937;font-size:20px;font-weight:800;")
        self.back_btn = QPushButton("返回大厅")
        self.hangup_btn = QPushButton("挂断")
        self.mute_btn = QPushButton("切换麦克风")
        self.video_btn = QPushButton("切换视频")
        top.addWidget(self.call_info, 1)
        top.addWidget(self.mute_btn)
        top.addWidget(self.video_btn)
        top.addWidget(self.hangup_btn)
        top.addWidget(self.back_btn)
        layout.addLayout(top)

        self.call_status = QLabel("状态：准备建立通话")
        self.call_status.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #dff4ff, stop:1 #cfe9ff);"
            "border:1px solid #9dcaeb;border-radius:10px;padding:8px 10px;color:#1f4c67;font-weight:700;font-size:12px;"
        )
        layout.addWidget(self.call_status)

        self.call_detail = QTextEdit()
        self.call_detail.setReadOnly(True)
        self.call_detail.setStyleSheet(
            "QTextEdit{background:#f9fdff;border:1px solid #b9d9f4;border-radius:14px;color:#244964;font-size:13px;padding:8px;}"
        )
        layout.addWidget(self.call_detail, 1)

        self.call_log = QTextEdit()
        self.call_log.setReadOnly(True)
        self.call_log.setStyleSheet(
            "QTextEdit{background:#ffffff;border:1px solid #d6e6f3;border-radius:14px;color:#35566f;font-size:12px;padding:8px;}"
        )
        layout.addWidget(self.call_log, 1)

        bottom = QHBoxLayout()
        bottom.addWidget(QLabel("通话号："))
        self.call_id_label = QLabel("-")
        bottom.addWidget(self.call_id_label)
        bottom.addStretch(1)
        layout.addLayout(bottom)

        self.back_btn.clicked.connect(self.hangup_and_back)
        self.hangup_btn.clicked.connect(self.hangup_and_back)
        self.mute_btn.clicked.connect(lambda: self._append_log("切换麦克风状态"))
        self.video_btn.clicked.connect(lambda: self._append_log("切换视频状态"))

    def _append_log(self, text: str):
        stamp = datetime.now().strftime("%H:%M:%S")
        self.lobby_log.append(f"[{stamp}] {text}")
        self.call_log.append(f"[{stamp}] {text}")

    def refresh_contacts(self):
        self.contacts_scroll.clear()
        ordered = sorted(self.contacts.values(), key=lambda c: (not c.get("online", False), c.get("name", ""), c.get("id", "")))
        for contact in ordered:
            item = QListWidgetItem()
            widget = self._contact_card(contact)
            item.setSizeHint(widget.sizeHint())
            self.contacts_scroll.addItem(item)
            self.contacts_scroll.setItemWidget(item, widget)
        self.status.setText("状态：联系人已刷新")
        self._append_log("刷新联系人列表")

    def _contact_card(self, contact: dict) -> QWidget:
        card = QPushButton()
        card.setCursor(Qt.PointingHandCursor)
        card.setEnabled(bool(contact.get("online", False)))
        online = bool(contact.get("online", False))
        name = str(contact.get("name", contact.get("id", ""))).strip()
        peer_id = str(contact.get("id", "")).strip()
        device = str(contact.get("device", "未知设备")).strip()
        card.setMinimumHeight(126)
        card.setMaximumHeight(126)
        bg = "#f9fcff" if online else "#f5f8fb"
        fg = "#244964" if online else "#9aa9b8"
        card.setStyleSheet(
            f"QPushButton{{border-radius:14px;border:1px solid #b9d9f4;background:{bg};"
            f"color:{fg};font-size:18px;font-weight:800;padding:24px 18px;text-align:left;}}"
            "QPushButton:hover{background:#f2f9ff;border:1px solid #8ec5ee;}"
            "QPushButton:disabled{border-color:#d8e3ec;}"
        )
        card.setText(f"{name}\n{peer_id}\n{device}  {'在线' if online else '离线'}")
        card.clicked.connect(lambda _checked=False, cid=peer_id: self.place_call(cid))
        return card

    def _find_contact(self, token: str) -> dict | None:
        key = (token or "").strip().lower()
        if not key:
            return None
        for contact in self.contacts.values():
            if key in str(contact.get("id", "")).lower() or key in str(contact.get("name", "")).lower():
                return contact
        return None

    def _call_selected(self):
        item = self.contacts_scroll.currentItem()
        if item is None:
            self.status.setText("状态：请先选择联系人")
            self.lobby_log.append("请先选择联系人")
            return
        widget = self.contacts_scroll.itemWidget(item)
        if widget is None:
            return
        text = widget.text().splitlines()[0].strip()
        contact = self._find_contact(text)
        if contact:
            self.place_call(contact["id"])

    def _call_from_input(self):
        contact = self._find_contact(self.call_target_edit.text())
        if contact is None:
            self.status.setText("状态：未找到可呼叫对象")
            self._append_log("未找到匹配联系人")
            return
        self.place_call(contact["id"])

    def place_call(self, peer_id: str):
        peer = self.contacts.get(peer_id)
        if not peer:
            self.status.setText("状态：联系人无效")
            self._append_log(f"联系人无效: {peer_id}")
            return
        if not peer.get("online", False):
            self.status.setText("状态：联系人离线")
            self._append_log(f"{peer.get('name', peer_id)} 当前离线")
            self._show_lobby()
            return
        self.pending_call_id = f"call_{int(datetime.now().timestamp() * 1000)}"
        self.active_call_id = self.pending_call_id
        self.active_peer_id = peer_id
        self.call_id_label.setText(self.active_call_id)
        self.call_info.setText(f"通话中：{peer.get('name', peer_id)}")
        self.call_status.setText("状态：通话请求已准备")
        self.call_detail.setPlainText(
            f"准备呼叫: {peer.get('name', peer_id)}\n"
            f"联系人ID: {peer_id}\n"
            f"设备: {peer.get('device', '未知')}\n"
            f"请求号: {self.active_call_id}"
        )
        self.call_log.clear()
        self._append_log(f"发起通话 -> {peer.get('name', peer_id)}")
        self.stack.setCurrentWidget(self.call_page)

    def on_incoming_call(self, call_id: str, from_id: str, from_name: str):
        self.pending_call_id = call_id
        self.active_call_id = call_id
        self.active_peer_id = from_id
        self.call_id_label.setText(call_id)
        self.call_info.setText(f"来电：{from_name}")
        self.call_status.setText("状态：有新的来电")
        self.call_detail.setPlainText(f"{from_name} 正在呼叫你\n来源ID: {from_id}\n通话号: {call_id}")
        self.call_log.clear()
        self._append_log(f"收到来电: {from_name}")
        self.stack.setCurrentWidget(self.call_page)

    def on_call_response(self, call_id: str, from_id: str, accepted: bool):
        if call_id != self.active_call_id:
            return
        self.call_status.setText("状态：对方已接听" if accepted else "状态：对方拒绝")
        self._append_log(f"{from_id} -> {'接听' if accepted else '拒绝'}")
        if not accepted:
            self.hangup_and_back()

    def on_call_hangup(self, call_id: str, from_id: str):
        if call_id == self.active_call_id:
            self._append_log(f"{from_id} 结束了通话")
            self.hangup_and_back()

    def hangup_and_back(self):
        if self.active_call_id:
            self._append_log(f"结束通话 {self.active_call_id}")
        self.active_call_id = ""
        self.active_peer_id = ""
        self.pending_call_id = ""
        self.call_id_label.setText("-")
        self.call_info.setText("通话中")
        self.call_status.setText("状态：返回大厅")
        self._show_lobby()

    def _show_lobby(self):
        self.stack.setCurrentWidget(self.lobby_page)
        self.status.setText("状态：回到大厅")

    def trigger_voice_action(self, action: str, payload: dict | None = None) -> bool:
        payload = payload or {}
        if action == "call_contact":
            target = str(payload.get("target", "")).strip()
            if target:
                contact = self._find_contact(target)
                if contact:
                    self.place_call(contact["id"])
                    return True
                self.call_target_edit.setText(target)
            self._call_from_input()
            return True
        if action == "hangup_call":
            self.hangup_and_back()
            return True
        if action == "refresh_contacts":
            self.refresh_contacts()
            return True
        return False
