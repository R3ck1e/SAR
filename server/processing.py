import json
import shutil
from pathlib import Path
from uuid import uuid4

import cv2
from ultralytics import YOLO

from config import (
    DEFAULT_MODEL,
    MODELS_DIR,
    PERSON_CLASS_ID,
    PROCESSED_META_DIR,
    RAW_FRAMES_DIR,
    UPLOADS_DIR,
    ensure_data_dirs,
)


class ProcessingError(RuntimeError):
    pass


def resolve_model_path(model_name: str = DEFAULT_MODEL) -> str:
    model_path = Path(model_name)
    if model_path.exists():
        return str(model_path)

    local_model_path = MODELS_DIR / model_name
    if local_model_path.exists():
        return str(local_model_path)

    return model_name


def extract_frames(video_path: Path, output_dir: Path, fps: float) -> int:
    if not video_path.exists():
        raise ProcessingError(f"Video file not found: {video_path}")

    if fps <= 0:
        raise ProcessingError("FPS must be greater than 0.")

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ProcessingError(f"Could not open video file: {video_path}")

    source_fps = capture.get(cv2.CAP_PROP_FPS)
    if source_fps <= 0:
        capture.release()
        raise ProcessingError("Could not determine source video FPS.")

    output_dir.mkdir(parents=True, exist_ok=True)
    frame_step = max(int(round(source_fps / fps)), 1)
    frame_index = 0
    saved_count = 0

    while True:
        success, frame = capture.read()
        if not success:
            break

        if frame_index % frame_step == 0:
            saved_count += 1
            frame_path = output_dir / f"frame_{saved_count:06d}.jpg"
            cv2.imwrite(str(frame_path), frame)

        frame_index += 1

    capture.release()
    return saved_count


def draw_detection(image, bbox, confidence: float, class_name: str) -> None:
    x1, y1, x2, y2 = [int(value) for value in bbox]
    label = f"{class_name} {confidence:.2f}"

    cv2.rectangle(image, (x1, y1), (x2, y2), (0, 180, 0), 2)
    cv2.putText(
        image,
        label,
        (x1, max(y1 - 8, 20)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 180, 0),
        2,
        cv2.LINE_AA,
    )


def run_inference(
    frames_dir: Path,
    detections_path: Path,
    annotated_dir: Path,
    conf: float,
    model_name: str = DEFAULT_MODEL,
) -> list[dict]:
    if not frames_dir.exists() or not frames_dir.is_dir():
        raise ProcessingError(f"Frames directory not found: {frames_dir}")

    if not 0 <= conf <= 1:
        raise ProcessingError("Confidence threshold must be between 0 and 1.")

    frame_paths = sorted(frames_dir.glob("*.jpg"))
    if not frame_paths:
        raise ProcessingError(f"No JPG frames found in: {frames_dir}")

    try:
        model = YOLO(resolve_model_path(model_name))
    except Exception as exc:
        raise ProcessingError(f"Could not load YOLO model '{model_name}': {exc}") from exc

    annotated_dir.mkdir(parents=True, exist_ok=True)
    detections = []

    for frame_index, frame_path in enumerate(frame_paths, start=1):
        image = cv2.imread(str(frame_path))
        if image is None:
            continue

        results = model.predict(source=image, conf=conf, verbose=False)

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                if class_id != PERSON_CLASS_ID:
                    continue

                confidence = float(box.conf[0].item())
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].tolist()]
                class_name = result.names.get(class_id, "person")

                detections.append(
                    {
                        "frame_name": frame_path.name,
                        "frame_index": frame_index,
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                        },
                    }
                )
                draw_detection(image, (x1, y1, x2, y2), confidence, class_name)

        cv2.imwrite(str(annotated_dir / frame_path.name), image)

    detections_path.parent.mkdir(parents=True, exist_ok=True)
    with detections_path.open("w", encoding="utf-8") as file:
        json.dump(detections, file, ensure_ascii=False, indent=2)

    return detections


def process_video(
    video_path: Path,
    fps: float,
    conf: float,
    model_name: str = DEFAULT_MODEL,
    job_id: str | None = None,
) -> dict:
    ensure_data_dirs()

    if job_id is None:
        job_id = f"{video_path.stem}_{uuid4().hex[:8]}"

    frames_dir = RAW_FRAMES_DIR / job_id
    detections_path = PROCESSED_META_DIR / f"{job_id}_detections.json"
    annotated_dir = PROCESSED_META_DIR / f"{job_id}_annotated"

    saved_frames = extract_frames(video_path, frames_dir, fps)
    detections = run_inference(frames_dir, detections_path, annotated_dir, conf, model_name)

    return {
        "job_id": job_id,
        "video_name": video_path.name,
        "saved_frames": saved_frames,
        "detections_count": len(detections),
        "detections_path": str(detections_path),
        "annotated_dir": str(annotated_dir),
        "detections": detections,
    }


def save_uploaded_video(source_file, filename: str, job_id: str) -> Path:
    ensure_data_dirs()
    suffix = Path(filename).suffix or ".mp4"
    upload_path = UPLOADS_DIR / f"{job_id}{suffix}"

    with upload_path.open("wb") as file:
        shutil.copyfileobj(source_file, file)

    return upload_path


def cleanup_job(job_id: str) -> None:
    paths = [
        RAW_FRAMES_DIR / job_id,
        PROCESSED_META_DIR / f"{job_id}_detections.json",
        PROCESSED_META_DIR / f"{job_id}_annotated",
    ]
    paths.extend(UPLOADS_DIR.glob(f"{job_id}.*"))

    for path in paths:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
