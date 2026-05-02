# SAR Pilot Console

Desktop client for the SAR processing pipeline.

The client is intended for the drone pilot's laptop:

- choose a video;
- choose local or remote processing;
- set FPS and confidence threshold;
- start analysis;
- view frames with detections.

## Development

Requirements:

- Go;
- Node.js;
- Wails CLI;
- Python environment for local processing.

Install Wails CLI:

```powershell
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

Run the client:

```powershell
cd client
npm install --prefix frontend
wails dev
```

Build desktop app:

```powershell
cd client
wails build
```

## Modes

Remote mode sends a video to:

```text
POST http://127.0.0.1:8000/api/analyze
```

Local mode runs:

```text
python server/process_video.py --video <selected_video> --fps <fps> --conf <conf>
```

For a production-like distribution, the pilot should receive a compiled `.exe` for Windows or `.app` for macOS. Docker is better suited for the remote processing server, not for the pilot-facing desktop app.

Local results are read from the shared project data directory:

```text
data/processed_meta/
```
