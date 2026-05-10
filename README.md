# SAR Drone Search Prototype

Прототип системы поиска людей на видеоданных с БПЛА. Проект разделен на две части:

```text
server/  - Python-backend обработки видео: OpenCV + YOLO + HTTP API
client/  - desktop-интерфейс пилота на Go + Wails
```

Идея архитектуры:

```text
[Wails client on ground station]
        |
        | video.mp4 + fps + confidence
        v
[Python processing server]
        |
        | detections.json + annotated frames
        v
[Wails result viewer]
```

Клиент может работать в двух режимах:

- `remote` - отправляет видео на сервер обработки;
- `local` - запускает тот же Python-конвейер на ноутбуке пилота.

Авторизация, база данных и личные кабинеты в прототип не добавлены: система рассчитана на локальный или закрытый контур наземной станции.

## Структура

```text
project/
├── server/
│   ├── api.py
│   ├── processing.py
│   ├── process_video.py
│   ├── extract_frames.py
│   ├── run_inference.py
│   ├── config.py
│   ├── Dockerfile
│   └── requirements.txt
├── client/
│   ├── app.go
│   ├── main.go
│   ├── wails.json
│   └── frontend/
├── data/
│   ├── uploads/
│   ├── raw_vids/
│   ├── raw_frames/
│   ├── processed_meta/
│   └── models/
└── README.md
```

## Быстрый тест server

Создать и активировать окружение:

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```powershell
pip install -r server\requirements.txt
```

Положить видео:

```text
data\raw_vids\example.mp4
```

Запустить полный конвейер локально:

```powershell
python server\process_video.py --video data\raw_vids\example.mp4 --fps 1 --conf 0.35
```

Результаты появятся здесь:

```text
data\processed_meta\example_detections.json
data\processed_meta\example_annotated\
```

## Запуск HTTP API

Из корня проекта:

```powershell
cd server
..\.venv\Scripts\python.exe -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Проверка:

```text
http://127.0.0.1:8000/api/health
```

Основные endpoints:

- `POST /api/analyze` - загрузить видео и запустить обработку;
- `GET /api/jobs` - список готовых заданий;
- `GET /api/jobs/{job_id}/detections` - JSON с обнаружениями;
- `GET /api/jobs/{job_id}/frames/{frame_name}` - аннотированный кадр;
- `DELETE /api/jobs/{job_id}` - удалить временные файлы задания.

## Запуск Wails-клиента

Понадобятся Go, Node.js и Wails CLI:

```powershell
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

Запуск в dev-режиме:

```powershell
cd client
npm install --prefix frontend
wails dev
```

Сборка desktop-приложения:

```powershell
cd client
wails build
```
