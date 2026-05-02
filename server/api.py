import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import DEFAULT_CONF, DEFAULT_FPS, DEFAULT_MODEL, PROCESSED_META_DIR, ensure_data_dirs
from processing import ProcessingError, cleanup_job, process_video, save_uploaded_video


app = FastAPI(title="SAR Processing Server", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    ensure_data_dirs()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze_video(
    video: UploadFile = File(...),
    fps: float = Form(DEFAULT_FPS),
    conf: float = Form(DEFAULT_CONF),
    model: str = Form(DEFAULT_MODEL),
) -> dict:
    job_id = uuid4().hex

    try:
        video_path = save_uploaded_video(video.file, video.filename, job_id)
        result = process_video(video_path, fps=fps, conf=conf, model_name=model, job_id=job_id)
    except ProcessingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    return {
        "job_id": result["job_id"],
        "video_name": result["video_name"],
        "saved_frames": result["saved_frames"],
        "detections_count": result["detections_count"],
        "detections_url": f"/api/jobs/{result['job_id']}/detections",
        "frames_url": f"/api/jobs/{result['job_id']}/frames/{{frame_name}}",
        "detections": result["detections"],
    }


@app.get("/api/jobs")
def list_jobs() -> list[dict]:
    ensure_data_dirs()
    jobs = []

    for json_path in sorted(PROCESSED_META_DIR.glob("*_detections.json")):
        job_id = json_path.name.replace("_detections.json", "")
        with json_path.open("r", encoding="utf-8") as file:
            detections = json.load(file)

        jobs.append(
            {
                "job_id": job_id,
                "detections_count": len(detections),
                "detections_url": f"/api/jobs/{job_id}/detections",
            }
        )

    return jobs


@app.get("/api/jobs/{job_id}/detections")
def get_detections(job_id: str) -> list[dict]:
    json_path = PROCESSED_META_DIR / f"{job_id}_detections.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Detections JSON not found.")

    with json_path.open("r", encoding="utf-8") as file:
        return json.load(file)


@app.get("/api/jobs/{job_id}/frames/{frame_name}")
def get_annotated_frame(job_id: str, frame_name: str) -> FileResponse:
    frame_path = PROCESSED_META_DIR / f"{job_id}_annotated" / Path(frame_name).name
    if not frame_path.exists():
        raise HTTPException(status_code=404, detail="Annotated frame not found.")

    return FileResponse(frame_path)


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str) -> dict:
    cleanup_job(job_id)
    return {"status": "deleted", "job_id": job_id}
