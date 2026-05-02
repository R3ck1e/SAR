import argparse
import sys
from pathlib import Path

from config import DEFAULT_FPS, RAW_FRAMES_DIR, ensure_data_dirs
from processing import ProcessingError, extract_frames


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract frames from an aerial video.")
    parser.add_argument("--video", required=True, help="Path to video file.")
    parser.add_argument("--fps", type=float, default=DEFAULT_FPS, help="Frames per second to save.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_path = Path(args.video)
    output_dir = RAW_FRAMES_DIR / video_path.stem

    try:
        ensure_data_dirs()
        saved_count = extract_frames(video_path, output_dir, args.fps)
    except ProcessingError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Saved frames: {saved_count}")
    print(f"Frames directory: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
