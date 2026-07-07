from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    edge_api_base: str = os.getenv("RDK_EDGE_API_BASE", "http://127.0.0.1:8090")
    edge_api_token: str = os.getenv("RDK_EDGE_API_TOKEN", "")
    output_dir: Path = Path(os.getenv("RDK_SHARE_OUTPUT_DIR", str(Path(__file__).resolve().parent.parent / "output")))
    default_student_id: str = os.getenv("RDK_STUDENT_ID", "rdk_student")
    default_student_name: str = os.getenv("RDK_STUDENT_NAME", "RDK学生")
    tailscale_upload_base: str = os.getenv("RDK_TAILSCALE_UPLOAD_BASE", "")


CONFIG = AppConfig()
