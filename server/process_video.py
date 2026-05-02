import argparse
import sys
from pathlib import Path

from config import DEFAULT_CONF, DEFAULT_FPS, DEFAULT_MODEL
from processing import ProcessingError, process_video


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process a video: frames -> YOLO -> JSON.")
    parser.add_argument("--video", required=True, help="Path to video file.")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS, help="Frames per second to save.")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF, help="Confidence threshold.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="YOLO model name or path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = process_video(
            video_path=Path(args.video),
            fps=args.fps,
            conf=args.conf,
            model_name=args.model,
            job_id=Path(args.video).stem,
        )
    except ProcessingError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Job: {result['job_id']}")
    print(f"Saved frames: {result['saved_frames']}")
    print(f"Detections: {result['detections_count']}")
    print(f"JSON: {result['detections_path']}")
    print(f"Annotated frames: {result['annotated_dir']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
