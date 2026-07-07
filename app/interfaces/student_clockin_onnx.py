from __future__ import annotations

import base64
from dataclasses import dataclass


@dataclass
class ClockinResult:
    user_id: str = ""
    user_name: str = ""
    score: float = 0.0
    emotion_type: str = "neutral"
    emotion_prob: float = 0.0


class StudentClockinONNXClient:
    def __init__(self, model_path: str = "", registry_path: str = ""):
        self.model_path = model_path
        self.registry_path = registry_path

    @staticmethod
    def image_to_base64(image_bytes: bytes) -> str:
        return base64.b64encode(image_bytes).decode("ascii")

    def recognize_and_detect_emotion(self, image_bytes: bytes | str) -> dict:
        raise RuntimeError("学生打卡 onnx 适配层已预留，请接入你的 onnx 模型后实现。")

