# SAR Processing Server

Python-backend for video processing:

```text
video.mp4 -> extracted frames -> YOLO person detection -> JSON + annotated frames
```

## Local Run

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r server\requirements.txt
```

Process one video from CLI:

```powershell
python server\process_video.py --video data\raw_vids\example.mp4 --fps 1 --conf 0.35
```

Run HTTP API:

```powershell
cd server
..\.venv\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```text
http://127.0.0.1:8000/api/health
```

## API

- `POST /api/analyze` - upload one video and process it.
- `GET /api/jobs` - list processed jobs.
- `GET /api/jobs/{job_id}/detections` - get JSON detections.
- `GET /api/jobs/{job_id}/frames/{frame_name}` - get annotated frame.
- `DELETE /api/jobs/{job_id}` - remove temporary job files.

## Docker

Docker is useful for a remote processing server:

```powershell
docker build -t sar-processing server
docker run --rm -p 8000:8000 sar-processing
```
