import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';
import {
  AnalyzeLocal,
  AnalyzeRemote,
  CheckServer,
  GetFrameURL,
  SelectVideo,
} from '../wailsjs/go/main/App';

type Detection = {
  frame_name: string;
  frame_index: number;
  class_name: string;
  confidence: number;
  bbox: Record<string, number>;
};

type AnalyzeResult = {
  mode: string;
  job_id: string;
  detections_count: number;
  detections: Detection[];
  annotated_dir?: string;
  server_url?: string;
};

function App() {
  const [videoPath, setVideoPath] = useState('');
  const [mode, setMode] = useState<'local' | 'remote'>('remote');
  const [serverURL, setServerURL] = useState('http://127.0.0.1:8000');
  const [fps, setFps] = useState(1);
  const [conf, setConf] = useState(0.35);
  const [status, setStatus] = useState('Готов к запуску');
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [selectedFrame, setSelectedFrame] = useState('');
  const [frameURL, setFrameURL] = useState('');

  const filteredDetections = useMemo(() => {
    return (result?.detections ?? []).filter((item) => item.confidence >= conf);
  }, [result, conf]);

  const frameNames = useMemo(() => {
    return Array.from(new Set(filteredDetections.map((item) => item.frame_name))).sort();
  }, [filteredDetections]);

  const currentFrameDetections = filteredDetections.filter((item) => item.frame_name === selectedFrame);

  async function pickVideo() {
    const selected = await SelectVideo();
    if (selected) {
      setVideoPath(selected);
      setResult(null);
      setSelectedFrame('');
      setFrameURL('');
    }
  }

  async function testServer() {
    try {
      setStatus('Проверяю сервер обработки...');
      const message = await CheckServer(serverURL);
      setStatus(message);
    } catch (error) {
      setStatus(String(error));
    }
  }

  async function analyze() {
    try {
      setStatus('Идет обработка видео...');
      setResult(null);
      setSelectedFrame('');
      setFrameURL('');

      const analysisResult =
        mode === 'remote'
          ? await AnalyzeRemote(videoPath, serverURL, fps, conf)
          : await AnalyzeLocal(videoPath, fps, conf);

      setResult(analysisResult);
      setStatus(`Готово. Найдено объектов: ${analysisResult.detections_count}`);

      const firstFrame = Array.from(new Set(analysisResult.detections.map((item) => item.frame_name))).sort()[0];
      if (firstFrame) {
        await openFrame(analysisResult, firstFrame);
      }
    } catch (error) {
      setStatus(String(error));
    }
  }

  async function openFrame(sourceResult: AnalyzeResult, frameName: string) {
    setSelectedFrame(frameName);
    const url = await GetFrameURL(sourceResult, frameName);
    setFrameURL(url);
  }

  async function onSelectFrame(frameName: string) {
    if (!result) return;
    await openFrame(result, frameName);
  }

  return (
    <main className="shell">
      <section className="toolbar">
        <div>
          <h1>Поиск людей с БПЛА</h1>
          <p>Наземная станция для запуска локальной или серверной обработки видео.</p>
        </div>
        <button onClick={pickVideo}>Выбрать видео</button>
      </section>

      <section className="layout">
        <aside className="panel">
          <label>
            Видео
            <input value={videoPath || 'Файл не выбран'} readOnly />
          </label>

          <label>
            Режим обработки
            <select value={mode} onChange={(event) => setMode(event.target.value as 'local' | 'remote')}>
              <option value="remote">Сервер обработки</option>
              <option value="local">Локально на ноутбуке</option>
            </select>
          </label>

          {mode === 'remote' && (
            <label>
              Адрес сервера
              <div className="inline">
                <input value={serverURL} onChange={(event) => setServerURL(event.target.value)} />
                <button onClick={testServer}>Проверить</button>
              </div>
            </label>
          )}

          <label>
            FPS извлечения
            <input type="number" min="0.1" step="0.1" value={fps} onChange={(event) => setFps(Number(event.target.value))} />
          </label>

          <label>
            Confidence: {conf.toFixed(2)}
            <input type="range" min="0" max="1" step="0.01" value={conf} onChange={(event) => setConf(Number(event.target.value))} />
          </label>

          <button className="primary" onClick={analyze} disabled={!videoPath}>
            Запустить анализ
          </button>

          <div className="status">{status}</div>
        </aside>

        <section className="viewer">
          <div className="frames">
            <h2>Кадры с обнаружениями</h2>
            {frameNames.length === 0 && <p className="muted">Результатов пока нет.</p>}
            {frameNames.map((frameName) => (
              <button
                key={frameName}
                className={frameName === selectedFrame ? 'selected' : ''}
                onClick={() => onSelectFrame(frameName)}
              >
                {frameName}
              </button>
            ))}
          </div>

          <div className="imagePane">
            {frameURL ? <img src={frameURL} alt={selectedFrame} /> : <div className="placeholder">Аннотированный кадр появится здесь</div>}
          </div>

          <div className="detections">
            <h2>Обнаружения</h2>
            {currentFrameDetections.map((item, index) => (
              <article key={`${item.frame_name}-${index}`}>
                <strong>
                  #{item.frame_index} {item.class_name} {item.confidence.toFixed(3)}
                </strong>
                <pre>{JSON.stringify(item.bbox, null, 2)}</pre>
              </article>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}

createRoot(document.getElementById('root')!).render(<App />);
