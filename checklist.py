#!/usr/bin/env python3
"""
Small CLI hackathon checklist.

Commands:
  add TEXT      - add a task (TEXT must not be empty)
  list          - list tasks
  done ID       - mark task ID as done
  remove ID     - remove task ID

Data persisted in JSON at ~/.local/share/hackathon-checklist/tasks.json
Atomic saves use tempfile + os.replace. Schema validated on load. If the
existing JSON file is malformed or fails schema validation, the program
will refuse to overwrite it.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

DATA_FILE = Path.home() / ".local" / "share" / "hackathon-checklist" / "tasks.json"


def error(msg: str) -> None:
    print(msg, file=sys.stderr)


def validate_schema(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("data is not an object")
    if "next_id" not in data or "tasks" not in data:
        raise ValueError("missing required keys")
    next_id = data["next_id"]
    tasks = data["tasks"]
    if type(next_id) is not int or next_id < 1:
        raise ValueError("next_id must be integer >= 1")
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list")
    seen_ids = set()
    for t in tasks:
        if not isinstance(t, dict):
            raise ValueError("each task must be an object")
        if "id" not in t or "text" not in t or "done" not in t:
            raise ValueError("task missing fields")
        if type(t["id"]) is not int or t["id"] < 1:
            raise ValueError("task id must be integer >= 1")
        if t["id"] in seen_ids:
            raise ValueError("duplicate task id")
        seen_ids.add(t["id"])
        if not isinstance(t["text"], str) or not t["text"].strip():
            raise ValueError("task text must be non-empty string")
        if not isinstance(t["done"], bool):
            raise ValueError("task done must be boolean")
    if next_id <= max(seen_ids, default=0):
        raise ValueError("next_id must exceed existing task IDs")
    return {"next_id": next_id, "tasks": tasks}


def load_data(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"next_id": 1, "tasks": []}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"malformed JSON: {e}")
    return validate_schema(data)


def save_data(path: Path, data: Dict[str, Any]) -> None:
    # shortcut: no concurrent-writer lock; add one if multiple processes edit tasks.
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)
    # Write to a temporary file in the same directory and atomically replace.
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=str(parent), delete=False, encoding="utf-8") as tf:
            tmp_path = Path(tf.name)
            json.dump(data, tf, ensure_ascii=False, indent=2)
            tf.flush()
            os.fsync(tf.fileno())
        # Atomic replace
        os.replace(str(tmp_path), str(path))
    finally:
        if tmp_path is not None and tmp_path.exists():
            # If replace succeeded, tmp_path won't exist; otherwise remove
            tmp_path.unlink()


def cmd_add(path: Path, text_parts: List[str]) -> int:
    text = " ".join(text_parts).strip()
    if not text:
        error("error: task text must not be empty")
        return 2
    try:
        data = load_data(path)
    except ValueError as e:
        error(f"error loading data: {e}")
        return 3
    new_id = data["next_id"]
    data["tasks"].append({"id": new_id, "text": text, "done": False})
    data["next_id"] = new_id + 1
    try:
        save_data(path, data)
    except Exception as e:
        error(f"error saving data: {e}")
        return 4
    print(new_id)
    return 0


def cmd_list(path: Path) -> int:
    try:
        data = load_data(path)
    except ValueError as e:
        error(f"error loading data: {e}")
        return 3
    tasks = sorted(data["tasks"], key=lambda t: t["id"])
    for t in tasks:
        mark = "x" if t["done"] else " "
        print(f"{t['id']}. [{mark}] {t['text']}")
    return 0


def find_task(tasks: List[Dict[str, Any]], task_id: int) -> Dict[str, Any] | None:
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None


def cmd_done(path: Path, task_id: int) -> int:
    try:
        data = load_data(path)
    except ValueError as e:
        error(f"error loading data: {e}")
        return 3
    t = find_task(data["tasks"], task_id)
    if t is None:
        error("error: no such task ID")
        return 2
    if t["done"]:
        # idempotent
        return 0
    t["done"] = True
    try:
        save_data(path, data)
    except Exception as e:
        error(f"error saving data: {e}")
        return 4
    return 0


def cmd_remove(path: Path, task_id: int) -> int:
    try:
        data = load_data(path)
    except ValueError as e:
        error(f"error loading data: {e}")
        return 3
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    after = len(data["tasks"])
    if before == after:
        error("error: no such task ID")
        return 2
    try:
        save_data(path, data)
    except Exception as e:
        error(f"error saving data: {e}")
        return 4
    return 0


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(prog="checklist")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("add").add_argument("text", nargs="+")
    commands.add_parser("list")
    for name in ("done", "remove"):
        commands.add_parser(name).add_argument("id", type=int)
    ns = parser.parse_args(argv)
    cmd = ns.command
    data_file = DATA_FILE
    if cmd == "add":
        return cmd_add(data_file, ns.text)
    if cmd == "list":
        return cmd_list(data_file)
    if cmd == "done":
        return cmd_done(data_file, ns.id)
    if cmd == "remove":
        return cmd_remove(data_file, ns.id)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, UnicodeError) as exc:
        error(f"error accessing data: {exc}")
        raise SystemExit(4)
