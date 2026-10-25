#!/usr/bin/env python3
"""sloth-tidy: a lazy file tidier powered by a local open-weight model (via Ollama).

Sorts and renames the clutter in a folder. Dry-run by default, fully undoable,
never overwrites, and nothing ever leaves your machine.
"""
import argparse, json, re, shutil, sys, urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/chat"
CATEGORIES = ["Documents", "Images", "Screenshots", "Receipts", "Code",
              "Archives", "Media", "Other"]
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".log", ".py", ".js", ".html", ".tex"}
EXT_MAP = {
    "Documents": {".pdf", ".doc", ".docx", ".odt", ".txt", ".md", ".pptx", ".xlsx"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".json"},
    "Archives": {".zip", ".tar", ".gz", ".7z", ".rar"},
    "Media": {".mp3", ".mp4", ".mov", ".wav", ".mkv"},
}
UNDO_LOG = ".sloth-undo.json"

SYSTEM = (
    "You tidy files. Given a file name and an optional text snippet, reply with "
    'ONLY JSON: {"category": one of %s, "new_name": "short-descriptive-kebab-case"}. '
    "new_name has no extension. If the current name is already good, keep it."
) % json.dumps(CATEGORIES)


def by_extension(path):
    for cat, exts in EXT_MAP.items():
        if path.suffix.lower() in exts:
            return {"category": cat, "new_name": slug(path.stem)}
    return {"category": "Other", "new_name": slug(path.stem)}


def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "file"


def snippet(path):
    if path.suffix.lower() in TEXT_EXT:
        try:
            return path.read_text(errors="ignore")[:600]
        except OSError:
            pass
    return ""


def ask_model(model, path):
    body = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"File: {path.name}\nSnippet: {snippet(path)}"},
        ],
    }
    req = urllib.request.Request(OLLAMA_URL, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(json.load(r)["message"]["content"])
    cat = data.get("category")
    return {"category": cat if cat in CATEGORIES else "Other",
            "new_name": slug(str(data.get("new_name") or path.stem))}


def build_plan(folder, model, use_llm):
    plan, taken, warned = [], set(), False
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name.startswith(".") or f.name == UNDO_LOG:
            continue
        try:
            if not use_llm:
                raise RuntimeError
            info = ask_model(model, f)
        except Exception:
            if use_llm and not warned:
                print("! Couldn't reach the local model; using file extensions instead.")
                warned = True
            info = by_extension(f)
        dest_dir = folder / info["category"]
        dest, n = dest_dir / (info["new_name"] + f.suffix.lower()), 1
        while dest.exists() or dest in taken:
            dest = dest_dir / f"{info['new_name']}-{n}{f.suffix.lower()}"
            n += 1
        taken.add(dest)
        plan.append((f, dest))
    return plan


def apply_plan(folder, plan):
    log = []
    for src, dest in plan:
        dest.parent.mkdir(exist_ok=True)
        shutil.move(str(src), str(dest))
        log.append([str(dest), str(src)])
    (folder / UNDO_LOG).write_text(json.dumps(log, indent=1))


def undo(folder):
    log_file = folder / UNDO_LOG
    if not log_file.exists():
        sys.exit("Nothing to undo.")
    for dest, src in reversed(json.loads(log_file.read_text())):
        if Path(dest).exists() and not Path(src).exists():
            shutil.move(dest, src)
    log_file.unlink()
    for cat in CATEGORIES:  # remove category folders we emptied
        d = folder / cat
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()
    print("Undone. Everything is back where it was.")


def main():
    p = argparse.ArgumentParser(description="Lazy local-AI file tidier.")
    p.add_argument("folder", type=Path)
    p.add_argument("--model", default="llama3.2:3b", help="any Ollama model")
    p.add_argument("--apply", action="store_true", help="actually move files")
    p.add_argument("--undo", action="store_true", help="revert the last run")
    p.add_argument("--no-llm", action="store_true", help="sort by extension only")
    a = p.parse_args()
    folder = a.folder.expanduser().resolve()
    if not folder.is_dir():
        sys.exit(f"Not a folder: {folder}")
    if a.undo:
        return undo(folder)
    plan = build_plan(folder, a.model, not a.no_llm)
    if not plan:
        return print("Already tidy. Nothing to do. 🦥")
    for src, dest in plan:
        print(f"{src.name}  ->  {dest.relative_to(folder)}")
    if a.apply:
        apply_plan(folder, plan)
        print(f"\nMoved {len(plan)} files. Run with --undo to revert.")
    else:
        print(f"\nDry run: {len(plan)} files. Add --apply to do it.")


if __name__ == "__main__":
    main()
