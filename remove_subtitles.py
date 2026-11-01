from pathlib import Path
import re
import shutil
import py_compile
from datetime import datetime

app = Path("app.py")
code = app.read_text(encoding="utf-8")
original = code

backup = Path(
    f"app.py.backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
)

def remove(pattern, description, flags=0):
    global code
    updated, count = re.subn(pattern, "", code, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Could not safely remove: {description}")
    code = updated
    print("Removed:", description)

try:
    # Remove SRT and ASS generator functions.
    remove(
        r"(?ms)^def write_srt\(.*?(?=^def clean_hinglish\()",
        "SRT and ASS generation functions"
    )

    # Remove Subtitle ON/OFF dropdown from frontend.
    remove(
        r'(?is)<label>Subtitles</label>\s*<select name="subtitles">.*?</select>',
        "Subtitle ON/OFF dropdown"
    )

    # Remove subtitle mention from app description.
    code = code.replace(
        "automatic vertical clips, burned-in subtitles.",
        "automatic vertical clips."
    )

    # Remove subtitle parameter from process_job.
    remove(
        r",\s*subtitles\s*=\s*True(?=\s*\):)",
        "process_job subtitle parameter"
    )

    # Remove SRT creation from rendering loop.
    remove(
        r"(?m)^\s*srt\s*=\s*outdir\s*/.*\n\s*write_srt\(.*\)\s*\n",
        "SRT file generation"
    )

    # Remove ASS generation and FFmpeg subtitle filter.
    remove(
        r"(?ms)^            if subtitles:\n.*?(?=^            cmd = \[)",
        "ASS generation and subtitle overlay"
    )

    # Remove subtitle parameter from FastAPI endpoint.
    remove(
        r",\s*subtitles\s*:\s*bool\s*=\s*Form\(True\)",
        "FastAPI subtitle parameter"
    )

    # Remove subtitle argument from background task.
    remove(
        r",\s*subtitles(?=\s*\))",
        "Background task subtitle argument"
    )

    # Verify that no subtitle code remains.
    remaining = re.findall(
        r"(?im)^.*(?:subtitle|write_ass|write_srt|ass_path|srt_path|\.srt|\.ass|ass=).*$",
        code
    )

    if remaining:
        raise RuntimeError(
            "Subtitle references still found:\n" + "\n".join(remaining)
        )

    # Save backup and updated app.
    shutil.copy2(app, backup)
    app.write_text(code, encoding="utf-8")

    # Check Python syntax.
    py_compile.compile("app.py", doraise=True)

    print("\nSUCCESS! Subtitle system completely removed.")
    print("Backup:", backup)
    print("Python syntax: OK")

except Exception as error:
    app.write_text(original, encoding="utf-8")
    print("\nERROR:", error)
    print("Original app.py restored.")
    raise

