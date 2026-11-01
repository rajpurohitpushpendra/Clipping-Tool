# QuickClip Local 🎬

**AI-Powered Local Video Clipping Tool**

QuickClip Local is a Python-based video clipping application that automatically transforms long-form videos into short-form vertical clips suitable for platforms like YouTube Shorts, Instagram Reels, and TikTok.

It uses speech transcription and lightweight content-selection heuristics to identify interesting moments, generate clips, and add subtitles — without requiring paid AI APIs.

## ✨ Features

- **YouTube Video Support:** Process videos using YouTube URLs.
- **Local Video Upload:** Upload your own video files.
- **Automatic Transcription:** Generate transcripts using Faster-Whisper.
- **Smart Clip Selection:** Identify potentially engaging moments using transcript-based heuristics.
- **Vertical Video Conversion:** Convert videos into a 9:16 format.
- **Subtitle Generation:** Generate and burn subtitles into clips.
- **Local Processing:** Run the application on your own machine.
- **Hindi Transliteration:** Support for Hindi transliteration.

## 🛠️ Tech Stack

- Python
- FastAPI
- Faster-Whisper
- OpenCV
- MediaPipe
- yt-dlp
- FFmpeg

## 📋 Requirements

- macOS
- Python 3.11
- FFmpeg
- Internet connection for initial model downloads

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/rajpurohitpushpendra/Clipping-Tool.git
cd Clipping-Tool
```

### 2. Install FFmpeg

```bash
brew install ffmpeg
```

### 3. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Run the application

```bash
chmod +x start.sh
./start.sh
```

Open your browser:

http://127.0.0.1:8000

## 📂 Project Structure

```text
Clipping-Tool/
├── app.py
├── models/
│   └── face_landmarker.task
├── requirements.txt
├── cleanup.py
├── remove_subtitles.py
├── start.sh
├── README.md
└── .gitignore
```

## ⚙️ How It Works

1. Upload a local video or provide a YouTube URL.
2. The application extracts and transcribes audio.
3. Transcript-based heuristics identify potential highlights.
4. Selected moments are extracted into individual clips.
5. Videos are converted into vertical format.
6. Subtitles are generated and embedded into the clips.
7. Processed videos are saved locally.

## ⚠️ Limitations

- Clip selection uses lightweight heuristics rather than a semantic AI model.
- Center cropping may not always keep the speaker in frame.
- YouTube downloads may be affected by platform restrictions.
- Processing speed depends on hardware and video duration.
- Job history is stored in memory and resets when the application restarts.

## 🔒 Privacy

Video processing is designed to run locally. Whisper models may be downloaded during initial setup. Do not upload videos you do not own or have permission to process.

## 📄 License

This project is currently shared for educational and portfolio purposes. A formal open-source license has not yet been added.
