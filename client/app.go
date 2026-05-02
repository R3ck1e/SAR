package main

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	wailsRuntime "github.com/wailsapp/wails/v2/pkg/runtime"
)

type App struct {
	ctx context.Context
}

type Detection struct {
	FrameName  string             `json:"frame_name"`
	FrameIndex int                `json:"frame_index"`
	ClassName  string             `json:"class_name"`
	Confidence float64            `json:"confidence"`
	BBox       map[string]float64 `json:"bbox"`
}

type AnalyzeResult struct {
	Mode            string      `json:"mode"`
	JobID           string      `json:"job_id"`
	DetectionsCount int         `json:"detections_count"`
	Detections      []Detection `json:"detections"`
	AnnotatedDir    string      `json:"annotated_dir"`
	ServerURL        string      `json:"server_url"`
}

type RemoteAnalyzeResponse struct {
	JobID           string      `json:"job_id"`
	DetectionsCount int         `json:"detections_count"`
	Detections      []Detection `json:"detections"`
}

func NewApp() *App {
	return &App{}
}

func (a *App) startup(ctx context.Context) {
	a.ctx = ctx
}

func (a *App) SelectVideo() (string, error) {
	return wailsRuntime.OpenFileDialog(a.ctx, wailsRuntime.OpenDialogOptions{
		Title: "Select aerial video",
		Filters: []wailsRuntime.FileFilter{
			{DisplayName: "Video files", Pattern: "*.mp4;*.mov;*.avi;*.mkv"},
		},
	})
}

func (a *App) CheckServer(serverURL string) (string, error) {
	serverURL = strings.TrimRight(serverURL, "/")
	if serverURL == "" {
		return "", errors.New("server URL is empty")
	}

	client := http.Client{Timeout: 5 * time.Second}
	response, err := client.Get(serverURL + "/api/health")
	if err != nil {
		return "", err
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		return "", fmt.Errorf("server returned %s", response.Status)
	}

	return "Server is available", nil
}

func (a *App) AnalyzeLocal(videoPath string, fps float64, conf float64) (*AnalyzeResult, error) {
	if videoPath == "" {
		return nil, errors.New("video file is not selected")
	}
	if _, err := os.Stat(videoPath); err != nil {
		return nil, fmt.Errorf("video file is not available: %w", err)
	}

	projectRoot, err := findProjectRoot()
	if err != nil {
		return nil, err
	}

	pythonPath := filepath.Join(projectRoot, ".venv", "Scripts", "python.exe")
	if runtime.GOOS != "windows" {
		pythonPath = filepath.Join(projectRoot, ".venv", "bin", "python")
	}
	if _, err := os.Stat(pythonPath); err != nil {
		pythonPath = "python"
	}

	serverDir := filepath.Join(projectRoot, "server")
	cmd := exec.Command(
		pythonPath,
		filepath.Join(serverDir, "process_video.py"),
		"--video", videoPath,
		"--fps", fmt.Sprintf("%.2f", fps),
		"--conf", fmt.Sprintf("%.2f", conf),
	)
	cmd.Dir = projectRoot

	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("local processing failed: %w\n%s", err, string(output))
	}

	jobID := strings.TrimSuffix(filepath.Base(videoPath), filepath.Ext(videoPath))
	detectionsPath := filepath.Join(projectRoot, "data", "processed_meta", jobID+"_detections.json")
	annotatedDir := filepath.Join(projectRoot, "data", "processed_meta", jobID+"_annotated")

	detections, err := readDetections(detectionsPath)
	if err != nil {
		return nil, err
	}

	return &AnalyzeResult{
		Mode:            "local",
		JobID:           jobID,
		DetectionsCount: len(detections),
		Detections:      detections,
		AnnotatedDir:    annotatedDir,
	}, nil
}

func (a *App) AnalyzeRemote(videoPath string, serverURL string, fps float64, conf float64) (*AnalyzeResult, error) {
	serverURL = strings.TrimRight(serverURL, "/")
	if serverURL == "" {
		return nil, errors.New("server URL is empty")
	}
	if videoPath == "" {
		return nil, errors.New("video file is not selected")
	}

	file, err := os.Open(videoPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)

	videoPart, err := writer.CreateFormFile("video", filepath.Base(videoPath))
	if err != nil {
		return nil, err
	}
	if _, err := io.Copy(videoPart, file); err != nil {
		return nil, err
	}

	_ = writer.WriteField("fps", fmt.Sprintf("%.2f", fps))
	_ = writer.WriteField("conf", fmt.Sprintf("%.2f", conf))
	if err := writer.Close(); err != nil {
		return nil, err
	}

	request, err := http.NewRequest(http.MethodPost, serverURL+"/api/analyze", &body)
	if err != nil {
		return nil, err
	}
	request.Header.Set("Content-Type", writer.FormDataContentType())

	client := http.Client{Timeout: 30 * time.Minute}
	response, err := client.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()

	responseBody, _ := io.ReadAll(response.Body)
	if response.StatusCode >= 300 {
		return nil, fmt.Errorf("remote processing failed: %s\n%s", response.Status, string(responseBody))
	}

	var remote RemoteAnalyzeResponse
	if err := json.Unmarshal(responseBody, &remote); err != nil {
		return nil, err
	}

	return &AnalyzeResult{
		Mode:            "remote",
		JobID:           remote.JobID,
		DetectionsCount: remote.DetectionsCount,
		Detections:      remote.Detections,
		ServerURL:        serverURL,
	}, nil
}

func (a *App) GetFrameURL(result AnalyzeResult, frameName string) (string, error) {
	if frameName == "" {
		return "", errors.New("frame name is empty")
	}

	if result.Mode == "remote" {
		return fmt.Sprintf("%s/api/jobs/%s/frames/%s", strings.TrimRight(result.ServerURL, "/"), result.JobID, frameName), nil
	}

	framePath := filepath.Join(result.AnnotatedDir, frameName)
	if _, err := os.Stat(framePath); err != nil {
		return "", err
	}

	return "file:///" + filepath.ToSlash(framePath), nil
}

func readDetections(path string) ([]Detection, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	var detections []Detection
	if err := json.Unmarshal(data, &detections); err != nil {
		return nil, err
	}

	return detections, nil
}

func findProjectRoot() (string, error) {
	candidates := []string{}

	if wd, err := os.Getwd(); err == nil {
		candidates = append(candidates, wd, filepath.Dir(wd))
	}

	if exe, err := os.Executable(); err == nil {
		dir := filepath.Dir(exe)
		candidates = append(candidates, dir, filepath.Dir(dir), filepath.Dir(filepath.Dir(dir)))
	}

	for _, candidate := range candidates {
		if _, err := os.Stat(filepath.Join(candidate, "server", "process_video.py")); err == nil {
			return candidate, nil
		}
	}

	return "", errors.New("project root with server/process_video.py was not found")
}
