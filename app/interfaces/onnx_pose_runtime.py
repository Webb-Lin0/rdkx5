from __future__ import annotations

from pathlib import Path
from typing import List

import cv2
import numpy as np


class PoseDetector:
    def __init__(self, model_path: str, *args, **kwargs):
        self.model_path = str(model_path)
        self._model_exists = Path(self.model_path).exists()
        self.input_size = int(kwargs.get("input_size", 416))

    def preprocess(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        size = self.input_size
        scale = min(size / max(1, h), size / max(1, w))
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        canvas = np.full((size, size, 3), 114, dtype=np.uint8)
        pad_x = (size - new_w) // 2
        pad_y = (size - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
        return canvas, scale, pad_x, pad_y

    def forward(self, input_tensor: np.ndarray):
        raise RuntimeError("onnx pose runtime not installed yet")

    def postprocess(self, output, frame_shape, scale: float, pad_x: int, pad_y: int) -> List[object]:
        return []


def draw_pose(frame: np.ndarray, poses, kpt_thres: float = 0.4):
    return frame

