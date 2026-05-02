import argparse
import sys
from pathlib import Path

from config import DEFAULT_CONF, DEFAULT_MODEL, PROCESSED_META_DIR, ensure_data_dirs
from processing import ProcessingError, run_inference


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run YOLO inference for extracted frames.")
    parser.add_argument("--frames", required=True, help="Path to frames directory.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="YOLO model name or path.")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF, help="Confidence threshold.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    frames_dir = Path(args.frames)
    job_id = frames_dir.name
    detections_path = PROCESSED_META_DIR / f"{job_id}_detections.json"
    annotated_dir = PROCESSED_META_DIR / f"{job_id}_annotated"

    try:
        ensure_data_dirs()
        detections = run_inference(
            frames_dir=frames_dir,
            detections_path=detections_path,
            annotated_dir=annotated_dir,
            conf=args.conf,
            model_name=args.model,
        )
    except ProcessingError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Detections: {len(detections)}")
    print(f"JSON: {detections_path}")
    print(f"Annotated frames: {annotated_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
