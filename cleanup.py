from pathlib import Path
from datetime import datetime
import os
import shutil

ROOT = Path(__file__).resolve().parent

# These folders/files will NEVER be deleted by this script.
PROTECTED = {
    ".venv",
    "models",
    "outputs",
    "output",
    "uploads",
    "downloads",
    ".git",
    "__pycache__",
}

BACKUP_PREFIXES = (
    "app.py.backup",
    "app.py.before",
    "app.py.frontend-backup",
)

SAFE_SUFFIXES = (
    ".pyc",
    ".tmp",
    ".temp",
    ".log",
)

def size_format(size):
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} TB"

def folder_size(path):
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file() and not item.is_symlink():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total

def is_protected(path):
    return any(part in PROTECTED for part in path.relative_to(ROOT).parts)

def is_cleanup_candidate(path):
    name = path.name.lower()

    if is_protected(path):
        return False

    if name.startswith(BACKUP_PREFIXES):
        return True

    if path.suffix.lower() in SAFE_SUFFIXES:
        return True

    if name == ".ds_store":
        return True

    if name == "__pycache__":
        return True

    return False

print("\n====================================")
print("       QUICKCLIP STORAGE AUDIT")
print("====================================\n")

all_files = []
candidates = []
total_size = 0

for path in ROOT.rglob("*"):
    if is_protected(path):
        continue

    if path.is_file() and not path.is_symlink():
        try:
            size = path.stat().st_size
            total_size += size
            all_files.append((size, path))

            if is_cleanup_candidate(path):
                candidates.append((size, path))
        except OSError:
            pass

print(f"Project: {ROOT}")
print(f"Files scanned: {len(all_files)}")
print(f"Total scanned size: {size_format(total_size)}")

print("\n========== LARGEST 20 FILES ==========\n")

for size, path in sorted(all_files, reverse=True)[:20]:
    print(f"{size_format(size):>10}  {path.relative_to(ROOT)}")

print("\n========== SAFE CLEANUP CANDIDATES ==========\n")

if not candidates:
    print("No safe cleanup candidates found.")
else:
    for size, path in sorted(candidates, reverse=True):
        print(f"{size_format(size):>10}  {path.relative_to(ROOT)}")

    reclaimable = sum(size for size, _ in candidates)
    print(f"\nPotential space recovery: {size_format(reclaimable)}")

    print("\nThese are backup/cache/temp files only.")
    answer = input("Delete ALL listed candidates? Type DELETE to confirm: ")

    if answer == "DELETE":
        deleted = 0

        for _, path in candidates:
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
                deleted += 1
                print("Deleted:", path.relative_to(ROOT))
            except OSError as e:
                print("Could not delete:", path, e)

        print(f"\nCleanup complete. Items deleted: {deleted}")
    else:
        print("\nNothing deleted. Audit only.")

print("\n========== AUDIT FINISHED ==========")
