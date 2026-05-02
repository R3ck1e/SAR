import os
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SERVER_ROOT.parent

DATA_DIR = Path(os.environ.get("SAR_DATA_DIR", PROJECT_ROOT / "data"))
UPLOADS_DIR = DATA_DIR / "uploads"
RAW_VIDS_DIR = DATA_DIR / "raw_vids"
RAW_FRAMES_DIR = DATA_DIR / "raw_frames"
PROCESSED_META_DIR = DATA_DIR / "processed_meta"
MODELS_DIR = DATA_DIR / "models"

DEFAULT_MODEL = "yolov8n.pt"
DEFAULT_FPS = 1
DEFAULT_CONF = 0.35

PERSON_CLASS_ID = 0


def ensure_data_dirs() -> None:
    for directory in (
        UPLOADS_DIR,
        RAW_VIDS_DIR,
        RAW_FRAMES_DIR,
        PROCESSED_META_DIR,
        MODELS_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
