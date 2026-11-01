import os, re, json, shutil, subprocess, threading, uuid
import cv2
from pathlib import Path
from datetime import timedelta
from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from faster_whisper import WhisperModel
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
import yt_dlp

BASE = Path(__file__).parent.resolve()
WORK = BASE / "work"
OUT = BASE / "output"
WORK.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)
app = FastAPI(title="QuickClip Local")
JOBS = {}
LOCK = threading.Lock()

HTML = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuickClip Local</title>

<style>
:root {
  color-scheme: dark;
  --bg: #080d1b;
  --panel: rgba(17, 25, 48, 0.92);
  --field: #0c1428;
  --border: rgba(142, 160, 220, 0.22);
  --text: #f1f5ff;
  --muted: #aab6d2;
  --blue: #7197ff;
  --purple: #a78bfa;
}
* { box-sizing: border-box; }
html { min-height: 100%; background: var(--bg); }
body {
  margin: 0;
  min-height: 100vh;
  padding: 42px 18px 64px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  color: var(--text);
  background:
    radial-gradient(ellipse at 12% 0%, rgba(55, 100, 220, .23), transparent 38%),
    radial-gradient(ellipse at 95% 12%, rgba(133, 75, 220, .20), transparent 34%),
    linear-gradient(145deg, #080d1b 0%, #0c1225 52%, #11102a 100%);
}
main {
  width: 100%;
  max-width: 820px;
  margin: 0 auto;
  padding: clamp(22px, 5vw, 38px);
  border: 1px solid var(--border);
  border-radius: 24px;
  background: var(--panel);
  box-shadow: 0 24px 80px rgba(0, 0, 0, .30);
  backdrop-filter: blur(14px);
}
h1 {
  margin: 0 0 12px;
  font-size: clamp(2rem, 5vw, 2.8rem);
  line-height: 1.15;
  letter-spacing: -0.045em;
  background: linear-gradient(100deg, #ffffff 12%, #a9c3ff 58%, #c6a8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
h2, h3 { color: #e7edff; letter-spacing: -.02em; }
p { line-height: 1.65; }
label {
  display: block;
  margin: 19px 0 8px;
  color: #d5def6;
  font-size: .94rem;
  font-weight: 600;
}
input, select, button, textarea {
  width: 100%;
  max-width: 100%;
  padding: 13px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--field);
  color: var(--text);
  font: inherit;
}
input, select, textarea { outline: none; }
input:focus, select:focus, textarea:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(113, 151, 255, .13);
}
input[type="file"] { padding: 10px; }
input::file-selector-button {
  margin-right: 12px;
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  background: #202d4e;
  color: #e5ebff;
  cursor: pointer;
}
button {
  margin-top: 20px;
  border: 0;
  background: linear-gradient(105deg, #527cf6, #8060e8);
  color: #fff;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(88, 103, 235, .20);
  transition: transform .18s ease, filter .18s ease;
}
button:hover { filter: brightness(1.1); transform: translateY(-1px); }
button:active { transform: translateY(0); }
small, .muted { color: var(--muted); }
a { color: #a9c6ff; text-underline-offset: 3px; }
a:hover { color: #d1c2ff; }
.job {
  margin: 16px 0;
  padding: 18px;
  overflow-wrap: anywhere;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: linear-gradient(145deg, rgba(23, 34, 63, .92), rgba(18, 19, 43, .92));
}
video {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: 12px;
  background: #050812;
}
hr { border: 0; border-top: 1px solid var(--border); }
::selection { background: rgba(113, 151, 255, .35); }
@media (max-width: 600px) {
  body { padding: 20px 12px 36px; }
  main { padding: 21px 16px; border-radius: 18px; }
  .job { padding: 14px; }
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; }
}

/* QuickClip video preview and download fixes */
.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  align-items: start;
}
.preview-frame {
  width: min(100%, 270px);
  aspect-ratio: 9 / 16;
  height: auto;
  overflow: hidden;
  border-radius: 12px;
  background: #050812;
  margin: 12px auto;
}
.preview-frame video {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  object-fit: contain;
  border-radius: 12px;
}
.download-btn {
  display: inline-block;
  margin: 8px 0;
  padding: 11px 18px;
  border-radius: 10px;
  background: linear-gradient(135deg, #536dfe, #9b5cff);
  color: white;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
}
.download-btn:hover { opacity: .9; }

.progress-wrap {
  margin: 14px 0 8px;
}
.progress-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  font-size: .88rem;
  color: #cbd7f5;
}
.progress-track {
  height: 11px;
  overflow: hidden;
  border-radius: 99px;
  background: #080e20;
  border: 1px solid var(--border);
}
.progress-fill {
  height: 100%;
  width: 0%;
  border-radius: inherit;
  background: linear-gradient(90deg, #527cf6, #a78bfa);
  box-shadow: 0 0 14px rgba(113,151,255,.4);
  transition: width .45s ease;
}
.progress-wrap.done .progress-fill {
  background: linear-gradient(90deg, #20c997, #58d68d);
}

</style>
</head><body><main><h1>🎬 QuickClip Local</h1>
<p class="muted">Local-first MVP: transcript heuristics, automatic vertical clips, automatic vertical clips. No paid AI API / no LLM.</p>
<form action="/create" method="post" enctype="multipart/form-data">
<label>YouTube URL (or leave blank to upload a video)</label><input name="url" type="url" placeholder="https://www.youtube.com/watch?v=...">
<label>Or upload video file</label><input name="video" type="file" accept="video/*">
<label>Number of clips (1–10)</label><select name="count">
<option value="1">1 clip</option><option value="2">2 clips</option>
<option value="3">3 clips</option><option value="4">4 clips</option>
<option value="5" selected>5 clips</option><option value="6">6 clips</option>
<option value="7">7 clips</option><option value="8">8 clips</option>
<option value="9">9 clips</option><option value="10">10 clips</option>
</select>
<label>Clip length</label><select name="length"><option value="30">30 seconds</option><option value="45" selected>45 seconds</option><option value="60">60 seconds</option></select>
<label>Transcription model (larger = usually more accurate, but slower)</label><select name="model"><option value="tiny">tiny (fastest)</option><option value="base">base</option><option value="small" selected>small (recommended)</option><option value="medium">medium (higher accuracy, slower)</option><option value="large-v3">large-v3 (best quality option, slowest)</option></select>

<button type="submit">Generate clips</button></form>
<p><small>Only process videos you own or have permission to use. YouTube downloading may fail due to platform restrictions; uploading a local file is the fallback.</small></p>
<h2>Recent jobs</h2>
<div id="jobs">Loading…</div>
<script>
let lastRenderedState = "";

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"
  }[c]));
}

async function refresh() {
  try {
    const response = await fetch("/jobs");
    const jobs = await response.json();
    const signature = JSON.stringify(jobs);

    // Do not rebuild video players unless job data changes.
    if (signature === lastRenderedState) return;
    lastRenderedState = signature;

    document.getElementById("jobs").innerHTML = jobs.map(job => {
      const items = job.clips?.length
        ? job.clips
        : (job.files || []).map(f => typeof f === "string" ? {file:f} : f);

      const cards = items.map((clip, i) => {
        const file = clip.file || "";
        const path = file.split("/").map(encodeURIComponent).join("/");
        const id = String(job.id || "job") + "-" + i;

        return `
          <article class="clip-card">
            <h3>${esc(file.split("/").pop() || "Your clip")}</h3>
            <div class="preview-frame">
              <video controls playsinline preload="metadata"
                src="/preview/${path}"></video>
            </div>
            <a class="download-btn" href="/files/${path}" target="_blank" rel="noopener">Download MP4</a>
          </article>`;
      }).join("");

      const progress = Math.max(0, Math.min(100, Number(job.progress || 0)));
      const done = job.status === "Done";
      const failed = job.status === "Failed";

      return `<section class="job">
        <b>${esc(job.status)}</b> — ${esc(job.message || "")}
        <div class="progress-wrap ${done ? "done" : ""}">
          <div class="progress-meta">
            <span>${esc(job.stage || job.message || "Waiting…")}</span>
            <strong>${failed ? "Error" : progress + "%"}</strong>
          </div>
          <div class="progress-track"
               role="progressbar"
               aria-valuemin="0"
               aria-valuemax="100"
               aria-valuenow="${progress}">
            <div class="progress-fill" style="width:${progress}%"></div>
          </div>
        </div>
        ${cards ? `<div class="preview-grid">${cards}</div>` : ""}
      </section>`;
    }).join("") || "No jobs yet";
  } catch (e) {
    console.error("Could not refresh jobs:", e);
  }
}

refresh();
setInterval(refresh, 3000);
</script></main></body></html>
"""

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p.stdout

def download_video(url, folder):
    opts = {
        "format": "bv*[height<=720]+ba/b[height<=720]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(folder / "source.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    candidates = list(folder.glob("source.*"))
    candidates = [p for p in candidates if p.suffix.lower() in {".mp4",".mkv",".webm",".mov"}]
    if not candidates:
        raise RuntimeError("Download did not produce a video file. Try uploading your own video file instead.")
    return candidates[0]

def clean_hinglish(text):
    """Keep English words, romanize Devanagari Hindi, and discard Arabic-script hallucinations."""
    text = str(text or "")
    text = re.sub(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+", " ", text)

    if re.search(r"[\u0900-\u097F]", text):
        text = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        # Make common ITRANS nasal spellings more readable in Roman Hinglish.
        text = text.replace(".n", "n").replace(".m", "m")
        text = text.replace("~N", "n").replace("~n", "n")

    text = re.sub(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def score_segment(words):
    text = " ".join(w["word"].lower() for w in words)
    score = 0.0
    keywords = ["because", "secret", "mistake", "important", "best", "worst", "never", "always",
                "problem", "solution", "why", "how", "truth", "actually", "imagine", "remember",
                "surprising", "result", "learned", "tip", "first", "finally", "but", "however"]
    score += sum(1.5 for k in keywords if re.search(r"\b"+re.escape(k)+r"\b", text))
    score += sum(1.0 for ch in "?!:" if ch in text)
    wc = len(words)
    score += min(wc / 18, 3.0)
    if wc < 35: score -= 2
    if wc > 150: score -= 1
    return score

def choose_segments(words, duration, count, length):
    # Make overlapping candidates, score transcript content, then pick spaced-out candidates.
    if duration <= length:
        return [(0.0, duration)]
    step = max(8, length // 5)
    candidates = []
    start = 0.0
    while start + min(length, duration-start) <= duration + 0.01:
        end = min(duration, start + length)
        seg = [w for w in words if w["end"] > start and w["start"] < end]
        if seg:
            score = score_segment(seg)
            # Prefer speech-dense segments, penalize mostly silent windows.
            speech = sum(max(0, min(w["end"], end)-max(w["start"], start)) for w in seg)
            score += min(speech / max(1, end-start), 1.0) * 2
            candidates.append((score, start, end))
        if end >= duration: break
        start += step
    picked = []
    min_gap = max(10, length * 0.55)
    for score, a, b in sorted(candidates, reverse=True):
        if all(abs(a-pa) >= min_gap for _, pa, _ in picked):
            picked.append((score,a,b))
        if len(picked) >= count: break
    if len(picked) < count:
        for score, a, b in sorted(candidates, reverse=True):
            if all(abs(a-pa) >= 3 for _,pa,_ in picked):
                picked.append((score,a,b))
            if len(picked) >= count: break
    return [(a,b) for _,a,b in sorted(picked, key=lambda x:x[1])]



def smart_crop_filter(source, start, end, words=None):
    """Detect and track faces; estimate the likely speaker from mouth motion
    during Whisper speech intervals, then frame that person's position.
    """
    fallback = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )

    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        print("[SpeakerCrop] Cannot open video; using fallback crop.")
        return fallback

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        cap.release()
        print("[SpeakerCrop] Invalid video dimensions; using fallback crop.")
        return fallback

    crop_w = int(height * 9 / 16)
    if width <= crop_w:
        cap.release()
        return fallback

    try:
        import mediapipe as mp
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        model_path = Path(__file__).resolve().parent / "models" / "face_landmarker.task"
        if not model_path.exists():
            raise FileNotFoundError(f"Face model not found: {model_path}")

        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=8,
            min_face_detection_confidence=0.45,
            min_face_presence_confidence=0.45,
            min_tracking_confidence=0.45,
        )

        # Whisper timestamps identify when speech is happening.
        speech_intervals = []
        for w in (words or []):
            try:
                a, b = float(w["start"]), float(w["end"])
                if b > a:
                    speech_intervals.append((a, b))
            except (KeyError, TypeError, ValueError):
                continue

        def is_speech(t):
            return any(a - 0.12 <= t <= b + 0.12 for a, b in speech_intervals)

        # Each track stores face position and mouth opening over time.
        tracks = []
        sample_fps = 5.0
        sample_count = min(100, max(8, int((end - start) * sample_fps) + 1))
        last_timestamp_ms = -1

        with vision.FaceLandmarker.create_from_options(options) as landmarker:
            for i in range(sample_count):
                t = start + (end - start) * i / max(1, sample_count - 1)
                cap.set(cv2.CAP_PROP_POS_MSEC, max(0, t) * 1000)
                ok, frame = cap.read()
                if not ok:
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                timestamp_ms = max(last_timestamp_ms + 1, int(t * 1000))
                last_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(image, timestamp_ms)

                detections = []
                for face in result.face_landmarks:
                    if len(face) <= 308:
                        continue

                    # Inner-lip opening divided by mouth width.
                    upper = face[13]
                    lower = face[14]
                    left = face[61]
                    right = face[291]

                    mouth_width = ((right.x - left.x) ** 2 +
                                   (right.y - left.y) ** 2) ** 0.5
                    if mouth_width < 0.001:
                        continue

                    mouth_open = (((lower.x - upper.x) ** 2 +
                                   (lower.y - upper.y) ** 2) ** 0.5) / mouth_width

                    # Face center from eye/cheek region, normalized to frame width.
                    cx = sum(face[j].x for j in (33, 133, 263, 362)) / 4
                    detections.append((cx * width, float(mouth_open)))

                # Greedy nearest-center tracking across adjacent frames.
                unmatched = set(range(len(tracks)))
                for cx, mouth in detections:
                    best_idx = None
                    best_dist = width * 0.18

                    for idx in unmatched:
                        previous = tracks[idx]["observations"][-1]
                        if t - previous[0] > 1.5:
                            continue
                        dist = abs(cx - previous[1])
                        if dist < best_dist:
                            best_dist = dist
                            best_idx = idx

                    if best_idx is None:
                        tracks.append({"observations": [(t, cx, mouth)]})
                    else:
                        tracks[best_idx]["observations"].append((t, cx, mouth))
                        unmatched.remove(best_idx)

        cap.release()
        cap = None

        if not tracks:
            print("[SpeakerCrop] No faces detected; using fallback crop.")
            return fallback

        # Score mouth movement only during detected speech.
        # A track needs enough speech-time observations to be considered.
        scored = []
        for track in tracks:
            obs = track["observations"]
            speech_obs = [o for o in obs if is_speech(o[0])]

            if len(speech_obs) < 3:
                continue

            movement = []
            for p, q in zip(speech_obs, speech_obs[1:]):
                if 0 < q[0] - p[0] <= 1.0:
                    movement.append(abs(q[2] - p[2]))

            if len(movement) < 2:
                continue

            # Reward repeated mouth movement during speech, not simply a large face.
            score = sum(movement) / len(movement)
            scored.append((score, track, speech_obs))

        if scored:
            scored.sort(key=lambda item: item[0], reverse=True)
            score, selected_track, selected_obs = scored[0]
            target_x = sorted(o[1] for o in selected_obs)[len(selected_obs) // 2]
            print(
                f"[SpeakerCrop] Likely speaker selected; "
                f"mouth-motion score={score:.4f}, "
                f"speech samples={len(selected_obs)}"
            )
        else:
            # No usable speech/mouth evidence: use the largest persistent face.
            selected_track = max(
                tracks,
                key=lambda tr: len(tr["observations"])
            )
            obs = selected_track["observations"]
            target_x = sorted(o[1] for o in obs)[len(obs) // 2]
            print("[SpeakerCrop] Speaker uncertain; framing the most consistently detected face.")

        crop_x = int(round(target_x - crop_w / 2))
        crop_x = max(0, min(width - crop_w, crop_x))

        # Preserve the original full-height 9:16 crop without extra zoom.
        scaled_w = round(width * 1920 / height)
        x_scaled = round(crop_x * 1920 / height)
        x_scaled = max(0, min(scaled_w - 1080, x_scaled))

        print(f"[SpeakerCrop] Crop position: {x_scaled}; source size: {width}x{height}")
        return f"scale=-2:1920,crop=1080:1920:x={x_scaled}:y=0"

    except Exception as exc:
        print(f"[SpeakerCrop] Detection error: {type(exc).__name__}: {exc}")
        print("[SpeakerCrop] Using fallback crop.")
        return fallback
    finally:
        if cap is not None:
            cap.release()


def process_job(job_id, source, model_name, count, length):
    jobdir = WORK / job_id
    outdir = OUT / job_id
    outdir.mkdir(parents=True, exist_ok=True)
    try:
        with LOCK: JOBS[job_id].update(status="Processing", message="Transcribing audio…", stage="Transcribing audio", progress=10)
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, info = model.transcribe(
            str(source),
            task="transcribe",
            language="hi",
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
            best_of=5,
            temperature=0,
            condition_on_previous_text=False,
            initial_prompt=(
                "Indian Hindi-English code-switching, commonly called Hinglish. "
                "Transcribe only words actually spoken in the audio. "
                "The speaker may switch between Hindi and English. "
                "Do not translate, summarize, or invent words."
            ),
        )
        words = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    cleaned = clean_hinglish(w.word)
                    if cleaned:
                        words.append({"start": float(w.start), "end": float(w.end), "word": cleaned})
            else:
                cleaned = clean_hinglish(seg.text)
                if cleaned:
                    words.append({"start": float(seg.start), "end": float(seg.end), "word": " " + cleaned})
        if not words:
            raise RuntimeError("No speech detected. Try another video or model.")
        duration = float(run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(source)]).strip())
        (jobdir/"transcript.json").write_text(json.dumps(words, ensure_ascii=False, indent=2), encoding="utf-8")
        (jobdir/"transcript.txt").write_text(" ".join(w["word"] for w in words), encoding="utf-8")
        picks = choose_segments(words, duration, count, length)
        files = []
        with LOCK:
            JOBS[job_id].update(
                message=f"Selected {len(picks)} clips. Preparing render…",
                stage="Preparing clips",
                progress=55
            )
        total_clips = len(picks)
        for i, (start,end) in enumerate(picks,1):
            clipname = f"clip_{i:02}.mp4"
            # Smart vertical crop: follow the most consistently detected face.
            vf = smart_crop_filter(source, start, end, words)


            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start:.3f}",
                "-i", str(source),
                "-t", f"{end-start:.3f}",
                "-vf", vf,
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "26",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(outdir / clipname)
            ]
            clip_duration = max(0.1, end - start)
            progress_cmd = cmd[:-1] + [
                "-progress", "pipe:1",
                "-nostats",
                cmd[-1]
            ]
            proc = subprocess.Popen(
                progress_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1
            )

            for line in proc.stdout:
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)

                if key == "out_time_ms":
                    try:
                        elapsed = int(value) / 1_000_000
                        fraction = min(1.0, max(0.0, elapsed / clip_duration))
                        overall = 60 + 35 * (
                            (i - 1 + fraction) / total_clips
                        )
                        with LOCK:
                            JOBS[job_id].update(
                                progress=int(overall),
                                stage=f"Rendering clip {i}/{total_clips}",
                                message=f"Rendering clip {i} of {total_clips}…"
                            )
                    except (ValueError, ZeroDivisionError):
                        pass

                elif key == "progress" and value == "end":
                    overall = 60 + 35 * (i / total_clips)
                    with LOCK:
                        JOBS[job_id].update(
                            progress=int(overall),
                            stage=f"Rendered clip {i}/{total_clips}",
                            message=f"Rendered {i} of {total_clips} clips…"
                        )

            return_code = proc.wait()
            if return_code != 0:
                raise RuntimeError(f"FFmpeg failed while rendering clip {i}")

            relfile = f"{job_id}/{clipname}"
            files.append(relfile)
        with LOCK: JOBS[job_id].update(status="Done", message=f"Created {len(files)} clips. Review the clips before posting.", stage="All clips ready", progress=100, files=files)
    except Exception as e:
        with LOCK: JOBS[job_id].update(status="Failed", message=str(e), stage="Processing failed", files=[])

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.post("/create")
async def create(background_tasks: BackgroundTasks, url: str = Form(""), count: int = Form(5), length: int = Form(45), model: str = Form("small"), video: UploadFile | None = File(None)):
    job_id = uuid.uuid4().hex[:8]
    jobdir = WORK / job_id
    jobdir.mkdir(parents=True, exist_ok=True)
    try:
        if video and video.filename:
            ext = Path(video.filename).suffix or ".mp4"
            source = jobdir / ("source" + ext)
            with source.open("wb") as f: shutil.copyfileobj(video.file, f)
        elif url.strip():
            with LOCK: JOBS[job_id] = {"id":job_id,"status":"Downloading","message":"Downloading video…","stage":"Downloading video","progress":2,"files":[]}
            source = download_video(url.strip(), jobdir)
        else:
            return HTMLResponse("Please provide a YouTube URL or upload a video. <a href='/'>Go back</a>", status_code=400)
        with LOCK:
            JOBS[job_id] = {"id":job_id,"status":"Queued","message":"Job started","stage":"Queued","progress":5,"files":[]}
        background_tasks.add_task(process_job, job_id, source, model, max(1,min(count,10)), max(15,min(length,120)))
    except Exception as e:
        with LOCK: JOBS[job_id] = {"id":job_id,"status":"Failed","message":str(e),"files":[]}
    return RedirectResponse("/", status_code=303)

@app.get("/jobs")
def jobs():
    return list(reversed(list(JOBS.values())))


@app.get("/preview/{path:path}")
async def preview(path: str, request: Request):
    p = (OUT / path).resolve()
    root = OUT.resolve()

    if not str(p).startswith(str(root) + "/") or not p.is_file():
        return HTMLResponse("Video not found", status_code=404)

    size = p.stat().st_size
    media_type = "video/mp4"
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(
            p,
            media_type=media_type,
            headers={"Accept-Ranges": "bytes"}
        )

    match = re.match(r"bytes=(\d*)-(\d*)$", range_header.strip())
    if not match:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{size}"}
        )

    first, last = match.groups()

    if first:
        start = int(first)
        end = int(last) if last else size - 1
    else:
        suffix = int(last or 0)
        if suffix <= 0:
            return Response(
                status_code=416,
                headers={"Content-Range": f"bytes */{size}"}
            )
        start = max(0, size - suffix)
        end = size - 1

    if start >= size or end < start:
        return Response(
            status_code=416,
            headers={"Content-Range": f"bytes */{size}"}
        )

    end = min(end, size - 1)
    length = end - start + 1

    def stream_file():
        with p.open("rb") as video:
            video.seek(start)
            remaining = length
            while remaining:
                chunk = video.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        stream_file(),
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        },
    )


@app.get("/files/{path:path}")
def files(path: str):
    from fastapi.responses import FileResponse, StreamingResponse, Response
    p = (OUT / path).resolve()
    if not str(p).startswith(str(OUT.resolve())) or not p.exists() or not p.is_file():
        return HTMLResponse("File not found", status_code=404)
    return FileResponse(p, filename=p.name)