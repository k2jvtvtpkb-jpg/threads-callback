"""投稿履歴・ネタ履歴の永続化（ローカルJSONファイル）。

リサーチャーの手薄ノード判定、ライターのパターンローテーション判定は
すべてこのファイルの内容を根拠にする。
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
HISTORY_PATH = DATA_DIR / "post_history.json"


def load_history():
    if not HISTORY_PATH.exists():
        return {"posts": []}
    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_history(history):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def append_post(history, post):
    """承認・却下を問わず、生成試行の記録を履歴に積む。"""
    history.setdefault("posts", []).append(post)
    save_history(history)
    return history


def recent_approved_patterns(history, n=3):
    """直近で承認され実際に採用されたポスト（=投稿候補）のパターンを新しい順にn件。"""
    approved = [p for p in history.get("posts", []) if p.get("status") == "approved"]
    approved_sorted = sorted(approved, key=lambda p: p.get("timestamp", ""))
    return [p["pattern"] for p in approved_sorted[-n:]]


def recent_titles_for_node(history, node_id, limit=5):
    """同一ノードで直近使ったネタタイトルを重複回避のために取得。"""
    posts = [
        p for p in history.get("posts", [])
        if p.get("node_id") == node_id and p.get("idea_title")
    ]
    posts_sorted = sorted(posts, key=lambda p: p.get("timestamp", ""), reverse=True)
    return [p["idea_title"] for p in posts_sorted[:limit]]
