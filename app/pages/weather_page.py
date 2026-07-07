from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, QThreadPool
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.interfaces.edge_gateway import EdgeGatewayClient
from app.workers import JsonWorker


class WeatherPage(QWidget):
    def __init__(self, client: EdgeGatewayClient | None = None):
        super().__init__()
        self.client = client or EdgeGatewayClient()
        self.pool = QThreadPool.globalInstance()
        self.current_location_name = "定位中..."
        self.current_data = {}
        self.compact_mode = False
        self._build_ui()
        self.update_time()
        self.refresh()
        self.time_timer = QTimer(self)
        self.time_timer.timeout.connect(self.update_time)
        self.time_timer.start(1000)

    def _build_ui(self):
        self.setStyleSheet("background:#f8f9fa;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(0)

        self.card_frame = QFrame()
        self.card_frame.setStyleSheet("QFrame{background:#fff;border:1px solid #dee2e6;border-radius:12px;}")
        self.card_layout = QHBoxLayout(self.card_frame)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.setSpacing(0)

        self.left_frame = QFrame()
        self.left_layout = QVBoxLayout(self.left_frame)
        self.top_info_label = QLabel("定位中...")
        self.top_info_label.setWordWrap(True)

        self.time_block = QWidget()
        time_layout = QVBoxLayout(self.time_block)
        time_layout.setContentsMargins(0, 0, 0, 0)
        self.time_label = QLabel("--:--")
        self.date_label = QLabel("--/-- --")
        self.temp_info_label = QLabel("-- ℃")
        for w in (self.time_label, self.date_label, self.temp_info_label):
            w.setAlignment(Qt.AlignCenter)
            time_layout.addWidget(w)

        self.daily_scroll = QScrollArea()
        self.daily_scroll.setWidgetResizable(True)
        self.daily_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.daily_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.daily_scroll.setFrameShape(QScrollArea.NoFrame)
        self.daily_scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.daily_host = QWidget()
        self.daily_layout = QHBoxLayout(self.daily_host)
        self.daily_layout.setContentsMargins(0, 0, 0, 0)
        self.daily_layout.setSpacing(8)
        self.daily_scroll.setWidget(self.daily_host)
        self.left_layout.addWidget(self.top_info_label)
        self.left_layout.addWidget(self.time_block, 1)
        self.left_layout.addWidget(self.daily_scroll)

        self.right_frame = QFrame()
        self.right_layout = QVBoxLayout(self.right_frame)
        self.right_title = QLabel("出行与生活建议")
        self.forecast_listbox = QListWidget()
        self.refresh_btn = QPushButton("刷新天气")
        self.refresh_btn.clicked.connect(self.refresh)
        self.right_layout.addWidget(self.right_title)
        self.right_layout.addWidget(self.forecast_listbox, 1)
        self.right_layout.addWidget(self.refresh_btn, 0, Qt.AlignRight)

        self.card_layout.addWidget(self.left_frame, 1)
        self.card_layout.addWidget(self.right_frame, 0)
        self.main_layout.addWidget(self.card_frame, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.update_scale_mode()

    def update_scale_mode(self):
        width = max(self.width(), self.parentWidget().width() if self.parentWidget() else 0)
        height = max(self.height(), self.parentWidget().height() if self.parentWidget() else 0)
        self.compact_mode = width <= 1024 or height <= 600
        left_margin = 10 if self.compact_mode else 20
        right_width = 230 if self.compact_mode else 280
        time_font = 42 if self.compact_mode else 82
        self.left_layout.setContentsMargins(left_margin, left_margin, left_margin, left_margin)
        self.left_layout.setSpacing(2 if self.compact_mode else 4)
        self.right_layout.setContentsMargins(8, 8, 8, 8)
        self.right_layout.setSpacing(4 if self.compact_mode else 5)
        self.right_frame.setFixedWidth(right_width)
        self.top_info_label.setStyleSheet("color:#0d6efd;font: bold 11px 'Microsoft YaHei';")
        self.time_label.setStyleSheet(f"color:#212529;font-size:{time_font}px;font-family:'DIN','Arial';font-weight:bold;")
        self.date_label.setStyleSheet("color:#6c757d;font-size:14px;font-weight:700;")
        self.temp_info_label.setStyleSheet("color:#212529;font-size:16px;font-weight:bold;")
        self.right_title.setStyleSheet("color:#212529;font-size:12px;font-weight:bold;")
        self.forecast_listbox.setStyleSheet(
            """
            QListWidget {
                background-color: #FCFDFF;
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px;
                font: 10px 'Microsoft YaHei';
            }
            QListWidget::item {
                height: 25px;
            }
            QScrollBar:vertical {
                width: 8px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: #bfd8ea;
                border-radius: 4px;
                min-height: 24px;
            }
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_scale_mode()
        if self.current_data:
            self._render_cached(self.current_data)

    @staticmethod
    def _first_text(rows):
        if not isinstance(rows, list):
            return ""
        for item in rows:
            if isinstance(item, dict):
                for key in ("category", "text", "summary", "name"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        return ""

    def refresh(self):
        self.top_info_label.setText("正在从边缘接口获取天气...")
        worker = JsonWorker(lambda: self.client.fetch_weather(""))
        worker.signals.success.connect(self._on_success)
        worker.signals.error.connect(self._on_error)
        self.pool.start(worker)

    def _extract(self, obj):
        data = obj.get("data", obj) if isinstance(obj, dict) else obj
        return data if isinstance(data, dict) else {}

    def _weather_icon(self, text: str) -> str:
        mapping = {"晴": "☀", "多云": "☁", "阴": "☁", "小雨": "🌧", "中雨": "🌧", "大雨": "🌧", "雷阵雨": "⛈"}
        return mapping.get(text or "", "☀")

    def _clear_daily(self):
        while self.daily_layout.count():
            item = self.daily_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_daily_card(self, item: dict):
        card = QFrame()
        card.setStyleSheet("QFrame{background:#FCFDFF;border:1px solid #DEE2E6;border-radius:12px;}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(4, 2, 4, 2)
        card_layout.setSpacing(0)
        date_label = QLabel(str(item.get("fxDate", "--"))[5:])
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setStyleSheet("color:#214761;font-size:9px;font-weight:800;")
        icon_label = QLabel(self._weather_icon(str(item.get("textDay", ""))))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color:#0D6EFD;font-size:12px;font-weight:900;")
        weather_label = QLabel(str(item.get("textDay", "未知")))
        weather_label.setAlignment(Qt.AlignCenter)
        weather_label.setStyleSheet("color:#4f6c83;font-size:9px;font-weight:700;")
        temp_label = QLabel(f"{item.get('tempMin', '--')}℃~{item.get('tempMax', '--')}℃")
        temp_label.setAlignment(Qt.AlignCenter)
        temp_label.setStyleSheet("color:#0D6EFD;font-size:9px;font-weight:800;")
        for w in (date_label, icon_label, weather_label, temp_label):
            card_layout.addWidget(w)
        card.setFixedHeight(96 if self.compact_mode else 112)
        card.setFixedWidth(82 if self.compact_mode else 92)
        self.daily_layout.addWidget(card)

    def _render_cached(self, data: dict):
        self.forecast_listbox.clear()
        self._clear_daily()

        now_data = data.get("now", {}).get("now", {}) if isinstance(data.get("now"), dict) else {}
        daily = data.get("daily", {}).get("daily", []) if isinstance(data.get("daily"), dict) else []
        air_indexes = data.get("air", {}).get("indexes", []) if isinstance(data.get("air"), dict) else []
        indices = data.get("indices", {}).get("daily", []) if isinstance(data.get("indices"), dict) else []
        if not indices and isinstance(data.get("indices"), dict):
            indices = data["indices"].get("list", []) if isinstance(data["indices"].get("list", []), list) else []

        now_text = str(now_data.get("text", "未知"))
        now_temp = str(now_data.get("temp", "--"))
        daily_max = str(daily[0].get("tempMax", "--")) if daily else "--"
        daily_min = str(daily[0].get("tempMin", "--")) if daily else "--"
        self.current_location_name = str(data.get("location_name") or data.get("location") or data.get("city") or "当前城市")
        air_text = self._first_text(air_indexes) if air_indexes else "未知"
        self.top_info_label.setText(f"{self.current_location_name} | {now_text} | 空气质量 {air_text}")
        self.temp_info_label.setText(f"{now_temp} ℃  |  今日 {daily_min} ℃ ~ {daily_max} ℃")

        for item in daily[:7]:
            if isinstance(item, dict):
                self._add_daily_card(item)

        self.forecast_listbox.addItem("出行与生活建议")
        self.forecast_listbox.addItem("-" * 20)
        for item in indices[:10]:
            if not isinstance(item, dict):
                continue
            display_text = f"{item.get('type', '')}: {item.get('category', '暂无')}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, item.get("text", "暂无详细说明"))
            self.forecast_listbox.addItem(list_item)

        def show_detail(item):
            detail_text = item.data(Qt.UserRole)
            if detail_text:
                QMessageBox.information(self, item.text(), str(detail_text))

        try:
            self.forecast_listbox.itemClicked.disconnect()
        except Exception:
            pass
        self.forecast_listbox.itemClicked.connect(show_detail)

    def _on_success(self, obj):
        data = self._extract(obj)
        self.current_data = data
        self._render_cached(data)
        self.update_time()

    def _on_error(self, message: str):
        self.top_info_label.setText("天气接口失败")
        self.temp_info_label.setText(message)
        self.forecast_listbox.clear()
        self.forecast_listbox.addItem(message)

    def update_time(self):
        now = datetime.now()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        self.time_label.setText(now.strftime("%H:%M"))
        self.date_label.setText(now.strftime(f"%Y/%m/%d {weekdays[now.weekday()]}"))
